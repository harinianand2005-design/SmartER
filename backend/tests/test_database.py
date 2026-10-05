from sqlalchemy import inspect, text

from app.db.session import engine


def test_database_connectivity_and_tables():
    with engine.connect() as connection:
        assert connection.execute(text("SELECT 1")).scalar_one() == 1
    tables = set(inspect(engine).get_table_names())
    expected = {"users", "er_metrics", "external_factors", "predictions", "resource_predictions", "alerts", "recommendations", "model_metrics"}
    assert expected.issubset(tables)