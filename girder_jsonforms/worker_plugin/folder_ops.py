from itertools import islice
from girder.constants import AccessType
from girder.models.folder import Folder
from girder.models.item import Item
from girder.models.user import User
from girder.utility.progress import ProgressContext
from girder_worker.app import app


@app.task(queue="local")
def delete_folder_task(
    folderId: str,
    progress: bool,
    userId: str,
    contentsOnly: bool = False,
):
    user = User().load(userId, force=True)
    folder = Folder().load(folderId, force=True)
    if not folder:
        return

    with ProgressContext(
        progress,
        user=user,
        title=f"Deleting folder {folder['name']}",
        message="Calculating folder size...",
    ) as ctx:
        if progress:
            total = Folder().subtreeCount(folder)
            if contentsOnly:
                total -= 1
            ctx.update(total=total)

        if contentsOnly:
            Folder().clean(folder, progress=ctx)
        else:
            Folder().remove(folder, progress=ctx)


def chunked_cursor(cursor, size):
    while True:
        chunk = list(islice(cursor, size))
        if not chunk:
            break
        yield chunk


def classify_ebsd(file_name: str, folder_name: str = "") -> str:
    name = (file_name or "").lower()
    folder = (folder_name or "").lower()

    raw_exts = (".ang", ".ctf", ".ebsd")
    script_exts = (".m", ".py", ".js", ".ipynb", ".mat")
    derived_exts = (
        ".png",
        ".jpg",
        ".jpeg",
        ".tif",
        ".tiff",
        ".bmp",
        ".gif",
        ".csv",
        ".tsv",
        ".xlsx",
        ".xls",
        ".pdf",
        ".ppt",
        ".pptx",
    )

    if name.endswith(raw_exts):
        return "EBSD_Raw"
    if name.endswith(script_exts):
        return "EBSD_Scripts"
    if name.endswith(derived_exts):
        return "EBSD_Derived"

    if "raw" in folder:
        return "EBSD_Raw"
    if "script" in folder or "scripts" in folder:
        return "EBSD_Scripts"
    if "derived" in folder or "map" in folder or "stats" in folder or "summary" in folder:
        return "EBSD_Derived"

    return "unknown"


def recursive_classify_ebsd(folder, user):
    for item in Folder().childItems(folder):
        item_meta = item.get("meta", {}) or {}
        item_type = classify_ebsd(item.get("name", ""), folder.get("name", ""))
        if item_type != "unknown":
            item_meta["data_type"] = item_type
            Item().setMetadata(item, item_meta)

    q = {
        "parentId": folder["_id"],
        "parentCollection": "folder",
    }
    for subfolder in Folder().findWithPermissions(
        q, user=user, level=AccessType.WRITE, limit=0, offset=0
    ):
        recursive_classify_ebsd(subfolder, user)


def recursive_assign_igsn(folder, user, igsn, progress):
    # Assign IGSN to items in the current folder
    for chunk in chunked_cursor(Folder().childItems(folder), 10000):
        document_ids = [doc["_id"] for doc in chunk]

        Item().collection.update_many(
            {"_id": {"$in": document_ids}}, {"$set": {"meta.igsn": igsn}}
        )

    q = {
        "parentId": folder["_id"],
        "parentCollection": "folder",
    }
    for subfolder in Folder().findWithPermissions(
        q, user=user, level=AccessType.WRITE, limit=0, offset=0
    ):
        progress.update(
            increment=1, message=f"Processing subfolder {subfolder['name']}"
        )
        recursive_assign_igsn(subfolder, user, igsn, progress)


@app.task(queue="local")
def classify_ebsd_folder_task(folderId: str, userId: str):
    user = User().load(userId, force=True)
    if user is None:
        return {"status": "error", "message": "user not found"}

    folder = Folder().load(folderId, force=True, user=user, level=AccessType.READ)
    if folder is None:
        return {"status": "error", "message": "folder not found"}

    recursive_classify_ebsd(folder, user)
    return {"status": "ok", "folderId": folderId}


@app.task(queue="local")
def assign_igsn_task(
    folderId: str,
    progress: bool,
    igsn: str,
    userId: str,
    itemsOnly: bool = False,
):
    user = User().load(userId, force=True)
    folder = Folder().load(folderId, user=user, level=AccessType.WRITE)
    with ProgressContext(
        progress,
        user=user,
        title=f"Assigning IGSN {igsn} to {folder['name']}",
        message="Recursing...",
    ) as ctx:
        recursive_assign_igsn(folder, user, igsn, ctx)
