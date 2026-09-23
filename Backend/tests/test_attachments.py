import pytest


@pytest.mark.parametrize("extension", ["xlsx", "xls", "docx", "doc", "pdf", "jpg", "jpeg", "png"])
def test_metadata_only(client, extension):
    result = client.post("/api/chat/attachments", data={"session_id": "demo"}, files={"file": (f"test.{extension}", b"synthetic bytes", "application/octet-stream")})
    assert result.status_code == 200
    assert result.json()["analyzed"] is False
    assert result.json()["size_bytes"] == 15 and result.json()["status"] == "metadata_only"


def test_reject_unsupported_and_empty(client):
    assert client.post("/api/chat/attachments", data={"session_id": "demo"}, files={"file": ("test.exe", b"no")}).status_code == 415
    assert client.post("/api/chat/attachments", data={"session_id": "demo"}, files={"file": ("test.pdf", b"")}).status_code == 422


def test_reject_oversized_upload_before_parsing(client):
    result = client.post("/api/chat/attachments", content=b"x", headers={"Content-Length": str(20 * 1024 * 1024), "Origin": "http://localhost:3000"})
    assert result.status_code == 413
    assert result.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_filename_is_metadata_not_a_path(client):
    result = client.post("/api/chat/attachments", data={"session_id": "demo"}, files={"file": ("../../test.pdf", b"metadata only")})
    assert result.json()["filename"] == "test.pdf"
