"""Module for the SQLite wrapper class."""
import os
import sqlite3
import pandas as pd


class Database:
    """
    SQLite Database wrapper with convenience functions.

    Parameters
    ----------
    filepath : str
        Path to the SQLite .db file.
    """

    def __init__(self, filepath):

        self._create_path(filepath)
        self._filepath = filepath

    @staticmethod
    def _create_path(filepath):
        """Creates the output path."""

        path = os.path.dirname(filepath)
        try:
            os.makedirs(path)
        except FileExistsError:
            pass

    def list_tables(self):
        """List tables in the database."""

        return self.query(
            "SELECT name, sql FROM sqlite_master WHERE type='table';"
        )

    def query(self, sql, parameters=None):
        """
        Execute the SQL statement against the database.

        Parameters
        ----------
        sql : str
            SQL query to perform
        parameters : Optional[dict]
            Parameters for the SQL query.

        Returns
        Union[pandas.DataFrame, int]
            Pandas DataFrame for SELECT queries,
            affected rows for all other queries.
        """

        connection = sqlite3.connect(self._filepath)
        with connection:
            cursor = connection.cursor()
            if parameters:
                result = cursor.execute(sql, parameters)
            else:
                result = cursor.execute(sql)

            # CREATE / INSERT / UPDATE queries
            if cursor.description is None:
                return result.rowcount

            # SELECT queries
            else:
                columns = [col[0] for col in cursor.description]
                df = pd.DataFrame(result.fetchall(), columns=columns)
                return df
