from __future__ import annotations
from typing import TYPE_CHECKING
from dataclasses import dataclass
from .action import Action, doc
from . import builtin

if TYPE_CHECKING:
    import transilience.system


@builtin.action(name="noop")
@dataclass
class Noop(Action):
    """
    Do nothing, successfully.
    """
    changed: bool = doc(False, "Set to True to pretend the action performed changes")

    def summary(self):
        return "Do nothing"

    def run(self, system: transilience.system.System):
        super().run(system)
        if self.changed:
            self.set_changed()


@builtin.action(name="fail")
@dataclass
class Fail(Action):
    """
    Fail with a custom message

    Same as Ansible's
    [builtin.fail](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/fail_module.html).
    """
    msg: str = "Failed as requested from task"

    def summary(self):
        return f"Fail: {self.msg}"

    def run(self, system: transilience.system.System):
        super().run(system)
        raise RuntimeError(self.msg)
