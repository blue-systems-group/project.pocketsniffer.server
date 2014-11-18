class BrokenState(Exception):
  pass

class EmptyState(Exception):
  pass

class BackendValidationError(Exception):
  pass

class DeviceDisabled(Exception):
  pass

class BackendDisabled(Exception):
  pass

class IdentifyError(Exception):
  pass

class AlreadyImported(Exception):
  pass

class LockTimeout(Exception):
  pass

class LockError(Exception):
  pass
