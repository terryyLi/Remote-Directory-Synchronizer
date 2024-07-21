
# Remote Directory Synchronizer

## Project Overview

**Remote Directory Synchronizer** is a Python-based solution for continuously replicating a source directory on one machine to a target directory on another machine. The synchronizer ensures that any changes in the source directory are mirrored in the target directory. The project uses a client-server model, with the `ReplicatorSource` representing the source directory and the `ReplicatorTarget` representing the target directory. The two components communicate via a Remote Procedure Call (RPC) mechanism to synchronize file system events.

## Features

- **Initial Synchronization**: Ensures that the target directory is an exact copy of the source directory during initialization.
- **Continuous Synchronization**: Monitors the source directory for changes and updates the target directory accordingly.
- **Efficient Synchronization**: Minimizes file writes by only updating files and directories that have changed.
- **Conflict Handling**: Handles conflicts between files and directories by ensuring the source structure is mirrored in the target.
- **Recursive Directory Watching**: Sets up watches on directories recursively to monitor and replicate changes.

## Usage

1. **Setup the FileSystem**: Implement the `FileSystem` interface to interact with your file system. The `FileSystem` interface includes methods for reading, writing, creating, and removing files and directories.

2. **Instantiate ReplicatorSource and ReplicatorTarget**: 
    ```python
    from file_system_impl import FileSystemImpl

    source_fs = FileSystemImpl()
    target_fs = FileSystemImpl()

    target = ReplicatorTarget(target_fs, "/target/path")
    source = ReplicatorSource(source_fs, "/source/path", target.handle_request)
    ```

3. **Run Tests**: Use the provided test suite to verify the functionality of the synchronizer.
    ```sh
    ./test.sh
    ```

## Project Structure

- `remote_file_replicator.py`: Contains the implementation of `ReplicatorSource` and `ReplicatorTarget`.
- `file_system.py`: Defines the `FileSystem` interface and related classes.
- `remote_file_replicator_test.py`: Test suite for verifying the functionality of the synchronizer.
- `file_system_impl.py`: Example implementation of the `FileSystem` interface for testing purposes.

## Example

Here's an example of how to use the Remote Directory Synchronizer:

```python
from file_system_impl import FileSystemImpl

source_fs = FileSystemImpl()
target_fs = FileSystemImpl()

# Initialize the replicator target and source
target = ReplicatorTarget(target_fs, "/target/path")
source = ReplicatorSource(source_fs, "/source/path", target.handle_request)

# The source directory is now being monitored, and changes will be replicated to the target directory
```

## Key Components

- **ReplicatorSource**: Monitors the source directory and sends RPC requests to the target for synchronization.
- **ReplicatorTarget**: Receives RPC requests from the source and updates the target directory accordingly.
- **FileSystem Interface**: Abstracts the file system operations to allow for testing and flexibility.
