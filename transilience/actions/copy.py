from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Union, List
from dataclasses import dataclass
import hashlib
import os
from .common import FileAction, PathObject
from . import builtin

if TYPE_CHECKING:
    import transilience.system


@builtin.action(name="copy")
@dataclass
class Copy(FileAction):
    """
    Same as Ansible's
    [builtin.copy](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/copy_module.html).

    Not yet implemented:

     * backup
     * decrypt
     * directory_mode
     * force
     * local_follow
     * remote_src
     * unsafe_writes
     * validate
     * src as directory
    """
    dest: str = ""
    src: Optional[str] = None
    content: Union[str, bytes, None] = None
    checksum: Optional[str] = None
    follow: bool = True

    def __post_init__(self):
        super().__post_init__()
        if self.dest == "":
            raise TypeError(f"{self.__class__}.dest cannot be empty")

        # If we are given a source file, compute its checksum
        if self.src is not None:
            if self.content is not None:
                raise ValueError(f"{self.__class__}: src and content cannot both be set")

            if self.checksum is None:
                self.src = os.path.abspath(self.src)
                with open(self.src, "rb") as fd:
                    self.checksum = PathObject.compute_file_sha1sum(fd)
        elif self.content is not None:
            if self.checksum is None:
                h = hashlib.sha1()
                if isinstance(self.content, str):
                    h.update(self.content.encode())
                else:
                    h.update(self.content)
                self.checksum = h.hexdigest()
        else:
            raise ValueError(f"{self.__class__}: one of src and content needs to be set")

    def summary(self):
        if self.content is not None:
            return "Replace contents of {self.dest!r}"
        else:
            return "Copy {self.src!r} to {self.dest!r}"

    def list_local_files_needed(self) -> List[str]:
        res = super().list_local_files_needed()
        if self.src is not None:
            res.append(self.src)
        return res

    def write_content(self):
        """
        Write destination file from self.content
        """
        path = self.get_path_object(self.dest)
        if path is not None:
            # If file exists, checksum it, and if the hashes are the same, don't transfer
            checksum = path.sha1sum()
            if checksum == self.checksum:
                self.set_path_object_permissions(path)
                return
            dest = path.path
        else:
            dest = self.dest

        if isinstance(self.content, str):
            content = self.content.encode()
        else:
            content = self.content

        with self.write_file_atomically(dest, "wb") as fd:
            fd.write(content)

    def write_src(self, system: transilience.system.System):
        """
        Write destination file from a streamed self.src
        """
        path = self.get_path_object(self.dest)
        if path is not None:
            # If file exists, checksum it, and if the hashes are the same, don't transfer
            checksum = path.sha1sum()
            if checksum == self.checksum:
                self.set_path_object_permissions(path)
                return
            dest = path.path
        else:
            dest = self.dest

        with self.write_file_atomically(dest, "w+b") as fd:
            system.transfer_file(self.src, fd)
            fd.seek(0)
            checksum = PathObject.compute_file_sha1sum(fd)
            if checksum != self.checksum:
                raise RuntimeError(f"{self.dest!r} has SHA1 {checksum!r} after receiving it,"
                                   f"but 'checksum' value is {self.checksum!r}")

    def run(self, system: transilience.system.System):
        super().run(system)
        if self.content is not None:
            self.write_content()
        else:
            self.write_src(system)
