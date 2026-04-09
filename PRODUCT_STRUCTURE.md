# Project Structure

This is a Python project with the following structure:

```
.
├── pytest.ini
├── requirements.txt
├── src/
│   ├── __init__.py
│   ├── __main__.py
│   ├── api.py
│   ├── config.py
│   ├── data_fetchers.py
│   ├── exceptions.py
│   ├── main.py
│   ├── models.py
│   └── service.py
└── tests/
    ├── __init__.py
    ├── test_data_fetchers.py
    └── test_service.py
```

## File Descriptions

- `pytest.ini`: Configuration file for pytest.
- `requirements.txt`: Lists the Python dependencies required for the project.
- `src/`: Contains the main source code of the project.
  - `__init__.py`: Makes the `src` directory a Python package.
  - `__main__.py`: Allows the package to be run as a script.
  - `api.py`: Likely contains API-related code.
  - `config.py`: Configuration settings for the project.
  - `data_fetchers.py`: Functions or classes for fetching data.
  - `exceptions.py`: Custom exceptions for the project.
  - `main.py`: The main entry point of the application.
  - `models.py`: Data models or classes representing data structures.
  - `service.py`: Service layer code, possibly for business logic.
- `tests/`: Contains test cases for the project.
  - `__init__.py`: Makes the `tests` directory a Python package.
  - `test_data_fetchers.py`: Tests for `data_fetchers.py`.
  - `test_service.py`: Tests for `service.py`.
  - `test_exceptions.py`: Tests for `exceptions.py`.

## Testing Guidelines

### Adding New Tests

1. **Create test file**: Create a new file in `tests/` named `test_<module_name>.py` corresponding to the source file in `src/`.

2. **Import setup**: Add path setup at the top of the test file to import from `src/`:
   ```python
   import sys
   from pathlib import Path
   
   # Add src directory to path
   sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
   ```

3. **Import modules**: Import the modules/classes to test directly (without `src.` prefix):
   ```python
   from exceptions import DXDataError, DataSourceError
   ```

4. **Test organization**: Use classes to organize tests by module/component:
   ```python
   class TestExceptionName:
       def test_feature(self):
           pass
   ```

5. **Run tests**: Execute tests using pytest:
   ```bash
   pytest tests/test_exceptions.py -v
   ```

### Existing Test Files

- `test_data_fetchers.py`: Tests for `data_fetchers.py` with timezone handling utilities
- `test_service.py`: Tests for `service.py`
- `test_exceptions.py`: Tests for `exceptions.py` covering all exception classes
