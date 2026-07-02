"""Unit and Integration tests for Knowledge Base Admin API (Task 15)."""

import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.tests.test_gateway import _make_token

@pytest.fixture(autouse=True)
def mock_pdf_reader(monkeypatch):
    class MockPage:
        def extract_text(self): return "Mock text"
    class MockReader:
        def __init__(self, stream):
            self.pages = [MockPage(), MockPage()]
    monkeypatch.setattr("rag.ingestor.pypdf.PdfReader", MockReader)

@pytest.fixture
def admin_token():
    return _make_token(user_id="admin1", role="government_officer", ward_ids=["*"])
    
@pytest.fixture
def leader_token():
    return _make_token(user_id="leader1", role="community_leader", ward_ids=["w1"])

@pytest.mark.asyncio
async def test_admin_rbac_rejection(leader_token):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Leader trying to list KB
        resp = await client.get("/admin/knowledge-base", headers={"Authorization": f"Bearer {leader_token}"})
        assert resp.status_code == 403

@pytest.mark.asyncio
async def test_upload_validation(admin_token):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Test non-PDF rejection
        files = {"file": ("test.txt", b"hello world", "text/plain")}
        resp1 = await client.post("/admin/knowledge-base", files=files, headers=headers)
        assert resp1.status_code == 400
        assert "Only PDF" in resp1.json()["detail"]
        
        # Test size limit (51MB)
        large_bytes = b"0" * (51 * 1024 * 1024)
        files2 = {"file": ("large.pdf", large_bytes, "application/pdf")}
        resp2 = await client.post("/admin/knowledge-base", files=files2, headers=headers)
        assert resp2.status_code == 413

@pytest.mark.asyncio
async def test_integration_upload_list_delete(admin_token):
    """15.6 Integration test for full admin lifecycle."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # 1. Upload valid PDF
        pdf_bytes = b"%PDF-1.4 Mock PDF Content\n\nPage 1\n\nPage 2"
        files = {"file": ("test_policy.pdf", pdf_bytes, "application/pdf")}
        resp_up = await client.post("/admin/knowledge-base", files=files, headers=headers)
        assert resp_up.status_code == 200
        assert resp_up.json()["status"] == "ingested"
        doc_id = resp_up.json()["document_id"]
        
        # 2. List documents
        resp_list = await client.get("/admin/knowledge-base", headers=headers)
        assert resp_list.status_code == 200
        docs = resp_list.json()
        assert isinstance(docs, list)
        assert len(docs) > 0
        
        # 3. Delete document
        resp_del = await client.delete(f"/admin/knowledge-base/{doc_id}", headers=headers)
        assert resp_del.status_code == 204
