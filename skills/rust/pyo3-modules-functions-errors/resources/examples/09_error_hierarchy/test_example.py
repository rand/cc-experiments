"""Tests for error_hierarchy example."""
import pytest
import error_hierarchy as eh

def test_exception_hierarchy():
    """Test exception inheritance structure."""
    assert issubclass(eh.DatabaseError, eh.AppError)
    assert issubclass(eh.ConnectionError, eh.DatabaseError)
    assert issubclass(eh.QueryError, eh.DatabaseError)
    
    assert issubclass(eh.NetworkError, eh.AppError)
    assert issubclass(eh.TimeoutError, eh.NetworkError)
    
    assert issubclass(eh.ValidationError, eh.AppError)

def test_connect_database():
    """Test database connection errors."""
    result = eh.connect_database("localhost", 5432)
    assert "Connected" in result
    
    with pytest.raises(eh.ConnectionError):
        eh.connect_database("", 5432)
    
    with pytest.raises(eh.ConnectionError):
        eh.connect_database("localhost", 9999)

def test_execute_query():
    """Test query execution errors."""
    result = eh.execute_query("SELECT * FROM users")
    assert len(result) > 0
    
    with pytest.raises(eh.QueryError):
        eh.execute_query("")
    
    with pytest.raises(eh.QueryError):
        eh.execute_query("DROP TABLE users")

def test_http_request():
    """Test HTTP request errors."""
    result = eh.http_request("https://example.com", 30)
    assert "Response" in result
    
    with pytest.raises(eh.HttpError):
        eh.http_request("ftp://example.com", 30)
    
    with pytest.raises(eh.TimeoutError):
        eh.http_request("https://slow.example.com", 1)

def test_validate_schema():
    """Test schema validation."""
    eh.validate_schema([("name", "Alice"), ("age", "30")])
    
    with pytest.raises(eh.SchemaError):
        eh.validate_schema([])
    
    with pytest.raises(eh.ConstraintError):
        eh.validate_schema([("name", "")])

def test_context_error():
    """Test error with context."""
    with pytest.raises(eh.ContextError) as exc_info:
        eh.complex_operation(-5)
    
    error = exc_info.value
    assert error.error_code == "ERR_NEGATIVE"
    assert len(error.context) > 0

def test_catch_base_exceptions():
    """Test catching base exceptions."""
    with pytest.raises(eh.DatabaseError):
        eh.connect_database("", 5432)
    
    with pytest.raises(eh.AppError):
        eh.connect_database("", 5432)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
