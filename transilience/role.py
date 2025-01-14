from __future__ import annotations
from typing import TYPE_CHECKING, Sequence, Optional, List, Union, Callable, Type, Set, Dict, Tuple
import contextlib
import warnings
import uuid
from . import actions
from .system import PipelineInfo

if TYPE_CHECKING:
    from .runner import Runner
    from transilience import template


ChainedMethod = Callable[[actions.Action], None]


class PendingAction:
    def __init__(
            self,
            role: "Role",
            action: actions.Action,
            notify: List[Type["Role"]],
            name: Optional[str] = None,
            then: Union[None, ChainedMethod, Sequence[ChainedMethod]] = None,
            ):
        self.name = name
        self.role = role
        self.action = action

        self.notify = notify

        self.then: List[ChainedMethod]
        if then is None:
            self.then = []
        elif callable(then):
            self.then = [then]
        else:
            self.then = list(then)

    @property
    def uuid(self):
        return self.action.uuid

    @property
    def summary(self):
        if self.name is None:
            self.name = self.action.summary()
        return self.name


class Role:
    """
    A collection of related actions to perform a provisioning macro-task on a
    system.

    The main point of a Role is to enqueue actions to be executed on a System,
    and possibly enqueue some more based on their results
    """
    def __init__(self):
        # Unique identifier for this role
        self.uuid: str = str(uuid.uuid4())
        self.name: Optional[str] = None
        self.template_engine: template.Engine
        self.runner: "Runner"
        self.pending: Set[str] = set()
        self.extra_when: Dict[Union[actions.Action, PendingAction], Union[str, List[str]]] = {}
        self.extra_notify: List[Type["Role"]] = []

    @contextlib.contextmanager
    def when(self, when: Dict[Union[actions.Action, PendingAction], Union[str, List[str]]]):
        """
        Add the given when rules to all actions added during the duration of this context manager.

        Multiple nested context managers add extra rules, and rules merge
        """
        orig_extra_when = self.extra_when
        try:
            self.extra_when = orig_extra_when.copy()
            self.extra_when.update(when)
            yield
        finally:
            self.extra_when = orig_extra_when

    @contextlib.contextmanager
    def notify(self, *args: Tuple[Type["Role"]]):
        """
        Add the given notify rules to all actions added during the duration of this context manager.

        Multiple nested context managers add extra notify entries, and the results merge
        """
        orig_extra_notify = self.extra_notify
        try:
            self.extra_notify = list(orig_extra_notify)
            self.extra_notify.extend(args)
            yield
        finally:
            self.extra_notify = orig_extra_notify

    def task(
            self,
            action: actions.Action,
            notify: Union[None, Type["Role"], Sequence[Type["Role"]]] = None,
            when: Optional[Dict[Union[actions.Action, PendingAction], Union[str, List[str]]]] = None,
            **kw):
        """
        Enqueue an action for execution
        """
        clean_notify: List[Type[Role]] = [] + self.extra_notify
        if notify is None:
            pass
        elif isinstance(notify, type):
            if not issubclass(notify, Role):
                raise RuntimeError("notify elements must be Role subclasses")
            clean_notify.append(notify)
        else:
            clean_notify.extend(notify)
        pa = PendingAction(self, action, notify=clean_notify, **kw)
        self.pending.add(action.uuid)
        self.runner.add_pending_action(pa)

        # Mark files for sharing
        for f in action.list_local_files_needed():
            # TODO: if it's a directory, share by prefix?
            self.runner.system.share_file(f)

        pipeline_info = PipelineInfo(self.uuid)

        if when is not None:
            pipe_when = {}
            for a, s in self.extra_when.items():
                if isinstance(s, str):
                    s = [s]
                pipe_when[a.uuid] = s
            for a, s in when.items():
                if isinstance(s, str):
                    s = [s]
                pipe_when[a.uuid] = s
            pipeline_info.when = pipe_when

        # File the action for execution
        self.runner.system.send_pipelined(action, pipeline_info)

        return pa

    def add(self, *args, **kw):
        warnings.warn("Role.add() has been renamed to Role.task()", DeprecationWarning)
        return self.task(*args, **kw)

    def on_action_executed(self, pending_action: PendingAction, action: actions.Action):
        """
        Called by the runner when an action has been executed
        """
        self.pending.discard(action.uuid)

        # Call chained callables, if any.
        # This can enqueue more tasks in the role
        for c in pending_action.then:
            c(action)

        # Mark role as done if there are no more tasks
        if not self.pending:
            self.close()
            # TODO: move the notification to runner
            from .runner import log
            log.info("%s", f"[done] {self.name}")

    def set_runner(self, runner: "Runner"):
        self.runner = runner
        self.template_engine = runner.template_engine

    def close(self):
        """
        Called when the role is done executing
        """
        self.runner.system.pipeline_close(self.uuid)

    def main(self):
        warnings.warn("Role.main() has been renamed to Role.start()", DeprecationWarning)
        return self.start()

    def start(self):
        raise NotImplementedError(f"{self.__class__}.start not implemented")
