# conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from selfai_ui.internal.db import Base, get_db  # your existing DB setup

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)          # create all tables
    Session = sessionmaker(bind=engine)
    session = Session()

    # Patch get_db to yield this session instead of the real one
    from contextlib import contextmanager
    @contextmanager
    def _mock_get_db():
        yield session

    import selfai_ui.internal.db as db_module
    import selfai_ui.models.job_windows as jw_module
    import selfai_ui.utils.gpu_queue as gq_module
    import selfai_ui.models.benchmark_config as bc_module
    original_db = db_module.get_db
    original_jw = jw_module.get_db
    original_gq = gq_module.get_db
    original_bc = bc_module.get_db

    db_module.get_db = _mock_get_db   # ← these four are missing
    jw_module.get_db = _mock_get_db
    gq_module.get_db = _mock_get_db
    bc_module.get_db = _mock_get_db

    yield session

    db_module.get_db = original_db
    jw_module.get_db = original_jw
    gq_module.get_db = original_gq
    bc_module.get_db = original_bc
    session.close()
    Base.metadata.drop_all(engine)
    
