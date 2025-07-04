"""Tests for MCP (Model Context Protocol) integration."""
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pathlib import Path
import json
import tempfile
import shutil

from claude_code_builder.mcp.mcp_handler import MCPHandler
from claude_code_builder.mcp.filesystem_handler import FilesystemHandler
from claude_code_builder.mcp.github_handler import GitHubHandler
from claude_code_builder.mcp.memory_handler import MemoryHandler
from claude_code_builder.mcp.search_handler import SearchHandler
from claude_code_builder.mcp.analysis_handler import AnalysisHandler
from claude_code_builder.mcp.development_handler import DevelopmentHandler
from claude_code_builder.models.mcp import MCPRequest, MCPResponse, MCPError
from claude_code_builder.exceptions.base import MCPError as MCPException


class TestMCPHandler:
    """Test suite for MCPHandler."""
    
    @pytest.fixture
    def mcp_config(self):
        """Create MCP configuration."""
        return {
            'filesystem': {
                'enabled': True,
                'path': '/usr/local/bin/mcp-filesystem',
                'args': ['--allow-write'],
                'allowed_paths': ['/tmp', '/workspace']
            },
            'github': {
                'enabled': True,
                'token': 'test-token',
                'rate_limit': 100
            },
            'memory': {
                'enabled': True,
                'db_path': ':memory:'
            }
        }
    
    @pytest.fixture
    def mcp_handler(self, mcp_config):
        """Create MCP handler instance."""
        return MCPHandler(config=mcp_config)
    
    @pytest.mark.asyncio
    async def test_initialize_handlers(self, mcp_handler):
        """Test MCP handler initialization."""
        await mcp_handler.initialize()
        
        # Check that enabled handlers are created
        assert 'filesystem' in mcp_handler.handlers
        assert 'github' in mcp_handler.handlers
        assert 'memory' in mcp_handler.handlers
        
        # Check handler types
        assert isinstance(mcp_handler.handlers['filesystem'], FilesystemHandler)
        assert isinstance(mcp_handler.handlers['github'], GitHubHandler)
        assert isinstance(mcp_handler.handlers['memory'], MemoryHandler)
    
    @pytest.mark.asyncio
    async def test_execute_request_success(self, mcp_handler):
        """Test successful MCP request execution."""
        # Initialize handlers
        await mcp_handler.initialize()
        
        # Mock filesystem handler
        mock_response = MCPResponse(
            id="test-123",
            result={"files": ["file1.py", "file2.py"]},
            success=True
        )
        mcp_handler.handlers['filesystem'].execute = AsyncMock(return_value=mock_response)
        
        # Create request
        request = MCPRequest(
            id="test-123",
            method="filesystem.list_files",
            params={"path": "/workspace"}
        )
        
        # Execute request
        response = await mcp_handler.execute_request(request)
        
        # Assertions
        assert response.success is True
        assert response.id == "test-123"
        assert "files" in response.result
        assert len(response.result["files"]) == 2
    
    @pytest.mark.asyncio
    async def test_execute_request_handler_not_found(self, mcp_handler):
        """Test request with unknown handler."""
        await mcp_handler.initialize()
        
        # Create request for unknown handler
        request = MCPRequest(
            id="test-456",
            method="unknown.action",
            params={}
        )
        
        # Execute request
        response = await mcp_handler.execute_request(request)
        
        # Should return error
        assert response.success is False
        assert "Unknown handler" in response.error.message
    
    @pytest.mark.asyncio
    async def test_execute_request_handler_error(self, mcp_handler):
        """Test request with handler error."""
        await mcp_handler.initialize()
        
        # Mock filesystem handler error
        error_response = MCPResponse(
            id="test-789",
            success=False,
            error=MCPError(code=-1, message="File not found")
        )
        mcp_handler.handlers['filesystem'].execute = AsyncMock(return_value=error_response)
        
        # Create request
        request = MCPRequest(
            id="test-789",
            method="filesystem.read_file",
            params={"path": "/nonexistent.txt"}
        )
        
        # Execute request
        response = await mcp_handler.execute_request(request)
        
        # Should return error
        assert response.success is False
        assert response.error.message == "File not found"
    
    @pytest.mark.asyncio
    async def test_batch_requests(self, mcp_handler):
        """Test executing multiple requests."""
        await mcp_handler.initialize()
        
        # Mock handlers
        fs_response = MCPResponse(id="req1", result={"content": "file content"}, success=True)
        github_response = MCPResponse(id="req2", result={"repo": "test-repo"}, success=True)
        
        mcp_handler.handlers['filesystem'].execute = AsyncMock(return_value=fs_response)
        mcp_handler.handlers['github'].execute = AsyncMock(return_value=github_response)
        
        # Create requests
        requests = [
            MCPRequest(id="req1", method="filesystem.read_file", params={"path": "test.py"}),
            MCPRequest(id="req2", method="github.get_repo", params={"owner": "test", "name": "repo"})
        ]
        
        # Execute batch
        responses = await mcp_handler.execute_batch(requests)
        
        # Assertions
        assert len(responses) == 2
        assert all(r.success for r in responses)
        assert responses[0].id == "req1"
        assert responses[1].id == "req2"


class TestFilesystemHandler:
    """Test suite for FilesystemHandler."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace."""
        workspace = Path(tempfile.mkdtemp())
        yield workspace
        shutil.rmtree(workspace, ignore_errors=True)
    
    @pytest.fixture
    def filesystem_handler(self, temp_workspace):
        """Create filesystem handler."""
        config = {
            'allowed_paths': [str(temp_workspace)],
            'max_file_size': 1024 * 1024  # 1MB
        }
        return FilesystemHandler(config=config)
    
    @pytest.mark.asyncio
    async def test_read_file(self, filesystem_handler, temp_workspace):
        """Test reading file."""
        # Create test file
        test_file = temp_workspace / "test.py"
        test_file.write_text("print('Hello, World!')")
        
        # Create request
        request = MCPRequest(
            id="read-test",
            method="read_file",
            params={"path": str(test_file)}
        )
        
        # Execute request
        response = await filesystem_handler.execute(request)
        
        # Assertions
        assert response.success is True
        assert response.result["content"] == "print('Hello, World!')"
        assert response.result["path"] == str(test_file)
    
    @pytest.mark.asyncio
    async def test_write_file(self, filesystem_handler, temp_workspace):
        """Test writing file."""
        file_path = temp_workspace / "new_file.py"
        content = "def hello():\n    return 'Hello!'"
        
        # Create request
        request = MCPRequest(
            id="write-test",
            method="write_file",
            params={"path": str(file_path), "content": content}
        )
        
        # Execute request
        response = await filesystem_handler.execute(request)
        
        # Assertions
        assert response.success is True
        assert file_path.exists()
        assert file_path.read_text() == content
        assert response.result["bytes_written"] == len(content)
    
    @pytest.mark.asyncio
    async def test_list_directory(self, filesystem_handler, temp_workspace):
        """Test listing directory."""
        # Create test files
        (temp_workspace / "file1.py").write_text("# File 1")
        (temp_workspace / "file2.js").write_text("// File 2")
        (temp_workspace / "subdir").mkdir()
        (temp_workspace / "subdir" / "file3.py").write_text("# File 3")
        
        # Create request
        request = MCPRequest(
            id="list-test",
            method="list_directory",
            params={"path": str(temp_workspace)}
        )
        
        # Execute request
        response = await filesystem_handler.execute(request)
        
        # Assertions
        assert response.success is True
        files = response.result["files"]
        assert len(files) >= 3  # file1.py, file2.js, subdir
        
        file_names = [f["name"] for f in files]
        assert "file1.py" in file_names
        assert "file2.js" in file_names
        assert "subdir" in file_names
    
    @pytest.mark.asyncio
    async def test_path_validation(self, filesystem_handler, temp_workspace):
        """Test path validation."""
        # Try to access path outside allowed paths
        forbidden_path = "/etc/passwd"
        
        request = MCPRequest(
            id="forbidden-test",
            method="read_file",
            params={"path": forbidden_path}
        )
        
        # Execute request
        response = await filesystem_handler.execute(request)
        
        # Should fail
        assert response.success is False
        assert "not allowed" in response.error.message.lower()


class TestGitHubHandler:
    """Test suite for GitHubHandler."""
    
    @pytest.fixture
    def github_handler(self):
        """Create GitHub handler."""
        config = {
            'token': 'test-token',
            'api_url': 'https://api.github.com',
            'rate_limit': 100
        }
        return GitHubHandler(config=config)
    
    @pytest.mark.asyncio
    async def test_get_repository(self, github_handler):
        """Test getting repository information."""
        # Mock GitHub API response
        mock_response = {
            'name': 'test-repo',
            'full_name': 'owner/test-repo',
            'description': 'Test repository',
            'default_branch': 'main',
            'language': 'Python'
        }
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            mock_get.return_value.__aenter__.return_value.status = 200
            
            # Create request
            request = MCPRequest(
                id="repo-test",
                method="get_repository",
                params={"owner": "owner", "name": "test-repo"}
            )
            
            # Execute request
            response = await github_handler.execute(request)
            
            # Assertions
            assert response.success is True
            assert response.result["name"] == "test-repo"
            assert response.result["language"] == "Python"
    
    @pytest.mark.asyncio
    async def test_list_files(self, github_handler):
        """Test listing repository files."""
        # Mock GitHub API response
        mock_response = [
            {
                'name': 'README.md',
                'path': 'README.md',
                'type': 'file',
                'size': 1024
            },
            {
                'name': 'src',
                'path': 'src',
                'type': 'dir'
            },
            {
                'name': 'main.py',
                'path': 'src/main.py',
                'type': 'file',
                'size': 2048
            }
        ]
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            mock_get.return_value.__aenter__.return_value.status = 200
            
            # Create request
            request = MCPRequest(
                id="files-test",
                method="list_files",
                params={"owner": "owner", "repo": "test-repo", "path": ""}
            )
            
            # Execute request
            response = await github_handler.execute(request)
            
            # Assertions
            assert response.success is True
            files = response.result["files"]
            assert len(files) == 3
            assert any(f["name"] == "README.md" for f in files)
            assert any(f["name"] == "main.py" for f in files)
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, github_handler):
        """Test rate limiting functionality."""
        # Simulate rate limit exceeded
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.return_value.status = 429
            mock_get.return_value.__aenter__.return_value.json = AsyncMock(return_value={
                'message': 'API rate limit exceeded'
            })
            
            # Create request
            request = MCPRequest(
                id="rate-test",
                method="get_repository",
                params={"owner": "owner", "name": "test-repo"}
            )
            
            # Execute request
            response = await github_handler.execute(request)
            
            # Should handle rate limiting
            assert response.success is False
            assert "rate limit" in response.error.message.lower()


class TestMemoryHandler:
    """Test suite for MemoryHandler."""
    
    @pytest.fixture
    def memory_handler(self):
        """Create memory handler."""
        config = {'db_path': ':memory:'}
        return MemoryHandler(config=config)
    
    @pytest.mark.asyncio
    async def test_store_memory(self, memory_handler):
        """Test storing memory."""
        await memory_handler.initialize()
        
        # Create request
        request = MCPRequest(
            id="store-test",
            method="store",
            params={
                "key": "project-info",
                "value": {"name": "test-project", "language": "Python"},
                "tags": ["project", "python"]
            }
        )
        
        # Execute request
        response = await memory_handler.execute(request)
        
        # Assertions
        assert response.success is True
        assert "stored" in response.result["message"].lower()
    
    @pytest.mark.asyncio
    async def test_retrieve_memory(self, memory_handler):
        """Test retrieving memory."""
        await memory_handler.initialize()
        
        # First store some data
        store_request = MCPRequest(
            id="store-first",
            method="store",
            params={
                "key": "test-data",
                "value": {"info": "test information"},
                "tags": ["test"]
            }
        )
        await memory_handler.execute(store_request)
        
        # Now retrieve it
        retrieve_request = MCPRequest(
            id="retrieve-test",
            method="retrieve",
            params={"key": "test-data"}
        )
        
        response = await memory_handler.execute(retrieve_request)
        
        # Assertions
        assert response.success is True
        assert response.result["value"]["info"] == "test information"
        assert "test" in response.result["tags"]
    
    @pytest.mark.asyncio
    async def test_search_memory(self, memory_handler):
        """Test searching memory."""
        await memory_handler.initialize()
        
        # Store multiple items
        items = [
            {"key": "python-tips", "value": {"tip": "Use list comprehensions"}, "tags": ["python", "tips"]},
            {"key": "js-tips", "value": {"tip": "Use arrow functions"}, "tags": ["javascript", "tips"]},
            {"key": "python-error", "value": {"error": "TypeError"}, "tags": ["python", "errors"]}
        ]
        
        for item in items:
            store_request = MCPRequest(id=f"store-{item['key']}", method="store", params=item)
            await memory_handler.execute(store_request)
        
        # Search for Python-related items
        search_request = MCPRequest(
            id="search-test",
            method="search",
            params={"tags": ["python"], "limit": 10}
        )
        
        response = await memory_handler.execute(search_request)
        
        # Assertions
        assert response.success is True
        results = response.result["results"]
        assert len(results) == 2  # python-tips and python-error
        assert all("python" in result["tags"] for result in results)


class TestSearchHandler:
    """Test suite for SearchHandler."""
    
    @pytest.fixture
    def search_handler(self):
        """Create search handler."""
        config = {
            'search_engines': ['google', 'bing'],
            'max_results': 10
        }
        return SearchHandler(config=config)
    
    @pytest.mark.asyncio
    async def test_web_search(self, search_handler):
        """Test web search functionality."""
        # Mock search results
        mock_results = [
            {
                'title': 'Python Documentation',
                'url': 'https://docs.python.org',
                'snippet': 'Official Python documentation'
            },
            {
                'title': 'Python Tutorial',
                'url': 'https://python.org/tutorial',
                'snippet': 'Learn Python programming'
            }
        ]
        
        with patch.object(search_handler, '_search_web', return_value=mock_results):
            # Create request
            request = MCPRequest(
                id="search-test",
                method="web_search",
                params={"query": "Python programming", "limit": 5}
            )
            
            # Execute request
            response = await search_handler.execute(request)
            
            # Assertions
            assert response.success is True
            results = response.result["results"]
            assert len(results) == 2
            assert results[0]["title"] == "Python Documentation"
    
    @pytest.mark.asyncio
    async def test_code_search(self, search_handler):
        """Test code search functionality."""
        # Mock code search results
        mock_results = [
            {
                'repository': 'owner/repo',
                'file': 'src/main.py',
                'line': 42,
                'content': 'def hello_world():',
                'url': 'https://github.com/owner/repo/blob/main/src/main.py#L42'
            }
        ]
        
        with patch.object(search_handler, '_search_code', return_value=mock_results):
            # Create request
            request = MCPRequest(
                id="code-search-test",
                method="code_search",
                params={"query": "hello_world function", "language": "python"}
            )
            
            # Execute request
            response = await search_handler.execute(request)
            
            # Assertions
            assert response.success is True
            results = response.result["results"]
            assert len(results) == 1
            assert "hello_world" in results[0]["content"]


@pytest.mark.integration
class TestMCPIntegration:
    """Integration tests for MCP system."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace."""
        workspace = Path(tempfile.mkdtemp())
        yield workspace
        shutil.rmtree(workspace, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_full_mcp_workflow(self, temp_workspace):
        """Test complete MCP workflow."""
        # Create MCP handler with real filesystem handler
        config = {
            'filesystem': {
                'enabled': True,
                'allowed_paths': [str(temp_workspace)]
            },
            'memory': {
                'enabled': True,
                'db_path': str(temp_workspace / 'memory.db')
            }
        }
        
        handler = MCPHandler(config=config)
        await handler.initialize()
        
        # 1. Create a file
        write_request = MCPRequest(
            id="create-file",
            method="filesystem.write_file",
            params={
                "path": str(temp_workspace / "test.py"),
                "content": "def hello():\n    return 'Hello, MCP!'"
            }
        )
        
        write_response = await handler.execute_request(write_request)
        assert write_response.success is True
        
        # 2. Read the file back
        read_request = MCPRequest(
            id="read-file",
            method="filesystem.read_file",
            params={"path": str(temp_workspace / "test.py")}
        )
        
        read_response = await handler.execute_request(read_request)
        assert read_response.success is True
        assert "Hello, MCP!" in read_response.result["content"]
        
        # 3. Store information in memory
        memory_request = MCPRequest(
            id="store-memory",
            method="memory.store",
            params={
                "key": "file-created",
                "value": {"file": "test.py", "status": "created"},
                "tags": ["file", "created"]
            }
        )
        
        memory_response = await handler.execute_request(memory_request)
        assert memory_response.success is True
        
        # 4. Retrieve from memory
        retrieve_request = MCPRequest(
            id="retrieve-memory",
            method="memory.retrieve",
            params={"key": "file-created"}
        )
        
        retrieve_response = await handler.execute_request(retrieve_request)
        assert retrieve_response.success is True
        assert retrieve_response.result["value"]["file"] == "test.py"
    
    @pytest.mark.asyncio
    async def test_mcp_error_handling(self, temp_workspace):
        """Test MCP error handling across handlers."""
        config = {
            'filesystem': {
                'enabled': True,
                'allowed_paths': [str(temp_workspace)]
            }
        }
        
        handler = MCPHandler(config=config)
        await handler.initialize()
        
        # Try to read non-existent file
        request = MCPRequest(
            id="read-missing",
            method="filesystem.read_file",
            params={"path": str(temp_workspace / "missing.py")}
        )
        
        response = await handler.execute_request(request)
        
        # Should handle error gracefully
        assert response.success is False
        assert response.error is not None
        assert "not found" in response.error.message.lower() or "no such file" in response.error.message.lower()