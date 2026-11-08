from os import environ


HOST_UPLOAD_TARGETS = {
    'gf': 'gofile',
    'bh': 'buzzheavier',
    'pd': 'pixeldrain',
    'stp': 'streamtape',
    'ab': 'akirabox',
    'vf': 'vikingfile',
    'fs': 'filester',
    'fm': 'filemirage',
    'tf': 'transferit',
    'st': 'storageto',
    'fb': 'filebin',
}

HOST_CREDENTIAL_VARS = {
    'gofile': 'GOFILE_API_KEY',
    'buzzheavier': 'BUZZHEAVIER_API_KEY',
    'pixeldrain': 'PIXELDRAIN_API_KEY',
    'streamtape': 'STREAMTAPE_CREDENTIALS',
    'akirabox': None,
    'vikingfile': 'VIKINGFILE_API_KEY',
    'filester': 'FILESTER_API_KEY',
    'filemirage': 'FILEMIRAGE_API_KEY',
    'transferit': None,
    'storageto': 'STORAGETO_API_KEY',
    'filebin': None,
}


def resolve_upload_host(destination: object) -> str | None:
    return HOST_UPLOAD_TARGETS.get(destination.casefold()) if isinstance(destination, str) else None


def upload_host_credential(host: str, settings: dict) -> str:
    entry = settings.get('upload_hosts', {}).get(host, (False, ''))
    credential = entry[1] if isinstance(entry, (list, tuple)) and len(entry) > 1 else ''
    if isinstance(credential, str) and credential.strip():
        return credential
    return environ.get(HOST_CREDENTIAL_VARS.get(host) or '', '')


def upload_host_credential_error(host: str, settings: dict) -> str | None:
    if host in ('akirabox', 'vikingfile', 'filester', 'filemirage', 'transferit', 'storageto', 'filebin'):
        return None
    names = {
        'gofile': 'GoFile',
        'buzzheavier': 'BuzzHeavier',
        'pixeldrain': 'PixelDrain',
        'streamtape': 'StreamTape',
    }
    credential = upload_host_credential(host, settings)
    if not isinstance(credential, str) or not credential.strip():
        return f'{names[host]} requires credentials. Set them in config.env before downloading.'
    if host == 'streamtape':
        login, separator, key = credential.partition(':')
        if not separator or not login.strip() or not key.strip():
            return 'StreamTape requires login:key credentials. Update them in config.env before downloading.'
    return None
