import pytest

from girder.models.collection import Collection
from girder.models.folder import Folder
from girder.models.item import Item

from ..worker_plugin import folder_ops

pytestmark = [
    pytest.mark.plugin("sample_tracker"),
    pytest.mark.plugin("wholetale"),
    pytest.mark.plugin("jsonforms"),
]


class TestEbsdFolderOperations:
    @pytest.mark.parametrize(
        "file_name,folder_name,expected",
        [
            ("scan.ctf", "", "EBSD_Raw"),
            ("scan.ang", "", "EBSD_Raw"),
            ("scan.ebsd", "", "EBSD_Raw"),
            ("process.py", "", "EBSD_Scripts"),
            ("process.m", "", "EBSD_Scripts"),
            ("process.js", "", "EBSD_Scripts"),
            ("process.ipynb", "", "EBSD_Scripts"),
            ("process.mat", "", "EBSD_Scripts"),
            ("map.png", "", "EBSD_Derived"),
            ("map.xlsx", "", "EBSD_Derived"),
            ("map.pdf", "", "EBSD_Derived"),
            ("map.pptx", "", "EBSD_Derived"),
            ("sample.dat", "raw scans", "EBSD_Raw"),
            ("sample.dat", "analysis scripts", "EBSD_Scripts"),
            ("sample.dat", "derived maps", "EBSD_Derived"),
            ("sample.dat", "other", "unknown"),
        ],
    )
    def test_classify_ebsd(self, file_name, folder_name, expected):
        assert folder_ops.classify_ebsd(file_name, folder_name) == expected

    def test_recursive_classify_ebsd_updates_nested_items(self, db, monkeypatch):
        root = {"_id": "root", "name": "Root"}
        nested = {"_id": "nested", "name": "raw data"}
        root_item = {"_id": "root-item", "name": "scan.ctf", "meta": {"existing": True}}
        nested_item = {"_id": "nested-item", "name": "unknown.dat", "meta": {}}
        metadata = []

        def child_items(_model, folder):
            return [root_item] if folder is root else [nested_item]

        def child_folders(_model, query, **_kwargs):
            return [nested] if query["parentId"] == "root" else []

        monkeypatch.setattr(Folder, "childItems", child_items)
        monkeypatch.setattr(Folder, "findWithPermissions", child_folders)
        monkeypatch.setattr(
            Item,
            "setMetadata",
            lambda _model, item, values: metadata.append((item, values.copy())),
        )
        folder_ops.recursive_classify_ebsd(root, object())

        assert metadata == [
            (
                root_item,
                {"existing": True, "data_type": "EBSD_Raw"},
            ),
            (
                nested_item,
                {"data_type": "EBSD_Raw"},
            ),
        ]

    def test_classify_ebsd_folder_task_returns_error_for_missing_folder(self, db, admin):
        assert folder_ops.classify_ebsd_folder_task.run(
            "000000000000000000000000", str(admin["_id"])
        ) == {
            "status": "error",
            "message": "folder not found",
        }
