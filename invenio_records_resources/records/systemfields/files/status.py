class FileStatus:
    """
    A namespace for file status. Can not be enum if we want to use the standard dict field,
    might be changed to enum if custom SystemField is used
    """

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"
