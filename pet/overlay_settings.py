"""Reuse PetInstance settings lifecycle without constructing a legacy pet window."""


def open_primary(overlay, identity):
    instance = overlay._instance
    opener = getattr(instance, 'open_modern_settings', None)
    if identity == getattr(instance.config, 'instance_id', '') and callable(opener):
        opener()
        return True
    return False


def open_in_process(overlay, identity):
    from .config import Config
    config = overlay._config
    shell = getattr(overlay._instance, 'shell', None)
    if not isinstance(config, Config) or shell is None or not hasattr(shell, '_instances'):
        return False
    from .app import PetInstance
    owners = getattr(overlay, '_settings_owners', None)
    if owners is None:
        owners = overlay._settings_owners = {}
        overlay.overlay.destroyed.connect(lambda: close_settings(overlay))
    owner = owners.get(identity)
    if owner is None:
        owner = PetInstance(shell, Config(base=config.dir.parent, instance_id=identity))
        owners[identity] = owner
    owner._open_modern_settings_in_process()
    dialog = owner.modern_settings_dialog
    if not getattr(dialog, '_overlay_settings_owned', False):
        dialog._overlay_settings_owned = True
        dialog.finished.connect(lambda *_: owners.pop(identity, None))
    return True


def close_settings(overlay):
    import shiboken6
    owners = getattr(overlay, '_settings_owners', {})
    for owner in list(owners.values()):
        dialog = owner.modern_settings_dialog
        if dialog is not None and shiboken6.isValid(dialog):
            dialog.close()
    owners.clear()
