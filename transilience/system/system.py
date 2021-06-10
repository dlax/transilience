from __future__ import annotations
from typing import TYPE_CHECKING, BinaryIO

if TYPE_CHECKING:
    from ..actions import Action


class System:
    """
    Access a system to be provisioned
    """

    def share_file(self, pathname: str):
        """
        Register a pathname as exportable to children
        """
        pass

    def share_file_prefix(self, pathname: str):
        """
        Register a pathname prefix as exportable to children
        """
        pass

    def create_pipeline(self) -> "Pipeline":
        """
        Create a new action pipeline
        """
        raise NotImplementedError(f"{self.__class__}.create_pipeline is not implemented")

    def transfer_file(self, src: str, dst: BinaryIO, **kw):
        """
        Fetch file ``src`` from the controller and write it to the open
        file descriptor ``dst``.
        """
        raise NotImplementedError(f"{self.__class__}.transfer_file is not implemented")


class Pipeline:
    """
    Abstract interface to a pipeline of actions.

    If an Action in the pipeline fails, all following actions will also fail,
    until reset() is called.
    """
    def add(self, action: Action):
        """
        Add an action to the execution pipeline
        """
        raise NotImplementedError(f"{self.__class__}.add is not implemented")

    def reset(self):
        """
        Reset the error status for the pipeline.

        If further actions are added, they will be executed normally
        """
        raise NotImplementedError(f"{self.__class__}.reset is not implemented")

    def close(self):
        """
        Cleanup after the pipeline is done.
        """
        raise NotImplementedError(f"{self.__class__}.close is not implemented")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
