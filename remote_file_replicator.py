"""Remote file replicator between a source and target directory."""

import posixpath
from typing import Any, Callable, Optional
from dataclasses import dataclass

from file_system import FileSystem
from file_system import FileSystemEvent
from file_system import FileSystemEventType

TASK_NUM = 1

@dataclass
class Request:
    command: str
    path: str
    data: Optional[str] = None

@dataclass
class Response:
    status: str
    message: Optional[str] = None
    data: Optional[Any] = None

class ReplicatorSource:
    """Class representing the source side of a file replicator."""

    def __init__(self, fs: FileSystem, dir_path: str, rpc_handle: Callable[[Any], Any]):
        self._fs = fs
        self._dir_path = dir_path
        self._rpc_handle = rpc_handle
        self._watched_dirs = set()

        self.initialize_target()
        self.sync_and_watch_directories(dir_path)
        
    def initialize_target(self):
        """Ensure that the target directory matches the source directory exactly."""
        # Get the target directory structure
        response = self._rpc_handle(Request(command='get_dir_structure', path=''))

        # Sync source to target, deleting any excess files/dirs in the target
        self.sync_target_with_source(self._dir_path, response.data)
        self.remove_excess_items(self._dir_path, response.data)

    def sync_target_with_source(self, src_dir, target_dir_structure: dict):
        """Sync the target directory with the source directory structure using DFS."""
        for item in self._fs.listdir(src_dir):
            src_path = posixpath.join(src_dir, item)
            relative_path = posixpath.relpath(src_path, self._dir_path)
            if self._fs.isdir(src_path):
                if relative_path not in target_dir_structure:
                    self._rpc_handle(Request(command='remove', path=relative_path))
                    self._rpc_handle(Request(command='makedir', path=relative_path))
                self.sync_target_with_source(src_path, target_dir_structure.get(relative_path, {}))
            else:
                content = self._fs.readfile(src_path)
                if relative_path not in target_dir_structure or target_dir_structure[relative_path] != content:
                    request = Request(command='writefile', path=relative_path, data=content)
                    self._rpc_handle(request)

    def remove_excess_items(self, src_dir, target_dir_structure: dict):
        """Remove excess items from the target directory that are not present in the source directory."""
        for relative_path, content in target_dir_structure.items():
            full_path = posixpath.join(src_dir, relative_path)
            if not self._fs.exists(posixpath.join(src_dir, relative_path)):
                self._rpc_handle(Request(command='remove', path=posixpath.relpath(full_path, self._dir_path)))
            elif isinstance(content, dict):
                # Recursively remove excess items
                self.remove_excess_items(posixpath.join(src_dir, relative_path), content)
    
    def sync_and_watch_directories(self, src_dir):
        # Watch the directory itself
        self._fs.watchdir(src_dir, self.handle_event)
        self._watched_dirs.add(src_dir)

        # Ensure the relative path is calculated correctly
        relative_path = posixpath.relpath(src_dir, self._dir_path)
        if relative_path != ".":
            request = Request(command='makedir', path=relative_path)
            self._rpc_handle(request)

        # Loop through each item in the directory
        for item in self._fs.listdir(src_dir):
            src_path = posixpath.join(src_dir, item)
            relative_path = posixpath.relpath(src_path, self._dir_path)
            if self._fs.isdir(src_path):
                request = Request(command='makedir', path=relative_path)
                self._rpc_handle(request)
                self.sync_and_watch_directories(src_path)
            else:
                content = self._fs.readfile(src_path)
                request = Request(command='writefile', path=relative_path, data=content)
                self._rpc_handle(request)

    def unwatch_prefix_directories(self, prefix_path):
        """Unwatch all directories that have prefix_path as their prefix."""
        to_unwatch = {dir_path for dir_path in self._watched_dirs if dir_path.startswith(prefix_path)}
        for dir_path in to_unwatch:
            self._fs.unwatchdir(dir_path)
            self._watched_dirs.remove(dir_path)

    def handle_event(self, event: FileSystemEvent):
        """Handle a file system event.

        Used as the callback provided to FileSystem.watchdir().
        """
        relative_path = posixpath.relpath(event.path, self._dir_path)

        match event.event_type:
            case FileSystemEventType.FILE_OR_SUBDIR_ADDED:
                if self._fs.isdir(event.path):
                    request = Request(command='makedir', path=relative_path)
                    self.sync_and_watch_directories(event.path)
                    self._rpc_handle(request)
                else:
                    content = self._fs.readfile(event.path)
                    request = Request(command='writefile', path=relative_path, data=content)
                    self._rpc_handle(request)

            case FileSystemEventType.FILE_OR_SUBDIR_REMOVED:
                self.unwatch_prefix_directories(event.path)
                request = Request(command='remove', path=relative_path)
                self._rpc_handle(request)
                
            case FileSystemEventType.FILE_MODIFIED:
                content = self._fs.readfile(event.path)
                request = Request(command='writefile', path=relative_path, data=content)
                self._rpc_handle(request)


class ReplicatorTarget:
    """Class representing the target side of a file replicator."""

    def __init__(self, fs: FileSystem, dir_path: str):
        self._fs = fs
        self._dir_path = dir_path

    def handle_request(self, request: Any) -> Any:
        """Handle a request from the ReplicatorSource."""
        req = request
        full_path = posixpath.join(self._dir_path, req.path)
        
        match req.command:
            case 'makedir':
                self._fs.makedirs(full_path)
            case 'writefile':
                if req.data is not None:
                    content = req.data
                    if self._fs.exists(full_path):
                        if self._fs.isdir(full_path):
                            self._fs.removedir(full_path)
                        else:
                            current_content = self._fs.readfile(full_path)
                            if current_content == content:
                                return
                    self._fs.writefile(full_path, content)
            case 'remove':
                if self._fs.exists(full_path):
                    if self._fs.isdir(full_path):
                        self._fs.removedir(full_path)
                    else:
                        self._fs.removefile(full_path)
            case 'get_dir_structure':
                dir_structure = self.get_dir_structure(self._dir_path)
                return Response(status='ok', data=dir_structure)
        
    def get_dir_structure(self, path: str) -> dict:
        """Get the directory structure for the given path."""
        structure = {}
        for item in self._fs.listdir(path):
            full_path = posixpath.join(path, item)
            if self._fs.isdir(full_path):
                structure[item] = self.get_dir_structure(full_path)
            else:
                structure[item] = self._fs.readfile(full_path)
        return structure