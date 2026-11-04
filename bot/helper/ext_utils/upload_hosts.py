HOST_UPLOAD_TARGETS = {
    'gf': 'gofile',
    'bh': 'buzzheavier',
    'pd': 'pixeldrain',
    'rnz': 'ranoz',
    'stp': 'streamtape',
}


def resolve_upload_host(destination: object) -> str | None:
    return HOST_UPLOAD_TARGETS.get(destination.casefold()) if isinstance(destination, str) else None


def upload_host_credential_error(host: str, settings: dict) -> str | None:
    names = {
        'gofile': 'GoFile',
        'buzzheavier': 'BuzzHeavier',
        'pixeldrain': 'PixelDrain',
        'ranoz': 'Ranoz',
        'streamtape': 'StreamTape',
    }
    entry = settings.get('upload_hosts', {}).get(host, (False, ''))
    credential = entry[1] if isinstance(entry, (list, tuple)) and len(entry) > 1 else ''
    if not isinstance(credential, str) or not credential.strip():
        return f'{names[host]} requires saved credentials. Add them in User Settings → Upload Hosts before downloading.'
    if host == 'streamtape':
        login, separator, key = credential.partition(':')
        if not separator or not login.strip() or not key.strip():
            return 'StreamTape requires saved login:key credentials. Update them in User Settings → Upload Hosts before downloading.'
    return None
