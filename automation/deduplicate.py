"""Exact file-content deduplication; never modifies source images."""
import hashlib


def group_images(files, metadata, previous=None):
    previous = previous or {}
    groups = {}
    for path in sorted(files, key=lambda p: p.name):
        digest = hashlib.sha256()
        with path.open('rb') as image:
            for chunk in iter(lambda: image.read(1024 * 1024), b''):
                digest.update(chunk)
        groups.setdefault(digest.hexdigest(), []).append(path)
    result = []
    for digest, members in groups.items():
        # Historical original wins; timestamp-based RPA filenames break ties.
        members.sort(key=lambda p: (p.name != previous.get(digest), p.name))
        result.append({'sha256': digest, 'primary': members[0], 'members': members})
    return sorted(result, key=lambda group: group['primary'].name)


def delete_duplicates(groups, image_directory):
    root = image_directory.resolve()
    deleted = []
    for group in groups:
        primary = group['primary']
        for duplicate in group['members'][1:]:
            if primary.is_symlink() or duplicate.is_symlink() or duplicate.resolve().parent != root or primary.resolve().parent != root:
                raise ValueError('Refusing to delete an image outside the image directory or a symlink')
            # Recheck immediately before deletion in case RPA is still writing.
            if hashlib.sha256(primary.read_bytes()).hexdigest() != group['sha256'] or hashlib.sha256(duplicate.read_bytes()).hexdigest() != group['sha256']:
                raise ValueError('Image changed during update; stop RPA and retry')
            duplicate.unlink()
            deleted.append(duplicate.name)
    return deleted
