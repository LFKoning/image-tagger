"""Module for the Images class."""
import os
import glob
import hashlib
import datetime as dt

import pandas as pd

from database import Database


class Images:
    """
    Images class that keeps track of tagged images.

    Parameters
    ----------
    config : config.ConfigReader
        ConfigReader configuration object.

    Methods
    -------
    first_untagged_id()
        Returns the first untagged image ID. If all images
        are tagged, the last image ID is returned.
    get(image_id)
        Returns the tag data for image with ID `image_id`.
    get(image_id)
        Returns the tag data for image with ID `image_id`.
    next_id(image_id)
        Returns the image ID succeeding the provided `image_id`.
    prev_id(image_id)
        Returns the image ID preceding the provided `image_id`.
    store(data)
        Stores the image tagging data. Data should be a dict contianing
        keys 'id', 'tags' and 'remark'.
    dump_data()
        Return the tagging data as a pandas DataFrame.
    """

    _index = 0
    _images = pd.DataFrame()

    def __init__(self, config):

        # Set up config and database
        self._config = config
        db_path = config.get("database/path", "image_tags.db")
        self._db = Database(db_path)

        self._initialize_database()
        self._load_images()

    def _load_images(self):
        """Loads images from the input path."""

        # Get untagged images
        path = self._config.get("images/path")
        types = self._config.get("images/types", ["jpg"])
        untagged = []
        for filetype in types:
            pattern = os.path.join(path, f"*.{filetype}")
            untagged.extend(glob.glob(pattern))

        if not untagged:
            raise RuntimeError(
                f"Did not find any images of in path '{path}' of types: '"
                + "', '".join(types) + "'."
            )

        # Load tag data
        tagged = self._db.query("SELECT * FROM tags")
        untagged = list(set(untagged) - set(tagged["path"]))

        # Merge the two sets
        untagged = pd.DataFrame(
            {"id": [self._hash(path) for path in untagged], "path": untagged,}
        )
        self._images = (
            pd.concat([tagged, untagged], axis=0)
            .sort_values(["updated", "path"])
            .reset_index(drop=True)
        )

        # Store IDs for fast indexing
        self._ids = list(self._images["id"])

    def first_untagged_id(self):
        """
        Get first untagged image ID.

        Returns
        -------
        str
            MD5 hash for the first untagged image. Returns the
            last image if all images have been tagged.
        """

        untagged = self._images.loc[self._images["updated"].isna(), "id"]
        if untagged.empty:
            # Return the last ID of the set
            return self._ids[-1]
        return untagged.iloc[0]

    def get(self, image_id):
        """
        Get image by ID and return it as dict.

        Parameters
        ----------
        image_id : str
            Image ID as an MD5 hash string.

        Returns
        -------
        dict
            Dict containing tagging data, including 'id', 'path',
            'tags', and 'remark'.
        """

        image = self._images.loc[self._images["id"] == image_id, :]
        if image.empty:
            raise RuntimeError(f"Cannot find image with ID '{image_id}'.")
        return dict(image.iloc[0])

    def _get_index(self, image_id):
        """
        Finds index value for the specified image ID.

        Parameters
        ----------
        image_id : str
            Image ID as an MD5 hash string.

        Returns
        -------
        int
            Index for provided ID or None if the ID was not found.
        """

        if image_id in self._ids:
            return self._ids.index(image_id)
        return None

    def next_id(self, image_id):
        """
        Get next ID from provided image ID.

        Parameters
        ----------
        image_id : str
            Image ID as an MD5 hash string.

        Returns
        -------
        str
            Image ID for the image succeeding the provided image ID.
        """

        idx = self._get_index(image_id)
        if idx < len(self._ids) - 1:
            return self._ids[idx + 1]
        return None

    def prev_id(self, image_id):
        """
        Get previous ID from given image ID.

        Parameters
        ----------
        image_id : str
            Image ID as an MD5 hash string.

        Returns
        -------
        str
            Image ID for the image preceding the provided image ID.
        """

        idx = self._get_index(image_id)
        if idx > 0:
            return self._ids[idx - 1]
        return None

    def store(self, data):
        """
        Stores image data if any changes were made.

        Parameters
        ----------
        data : dict
            Tagging data, should contain keys 'id', 'tags', 'remark'.
            All values should be provided as string values.
        """

        # Check required keys
        required = "id", "tags", "remark"
        missing = set(required) - set(data)
        if missing:
            raise KeyError(
                "Missing the following keys from tag data: " + ", ".join(missing)
            )

        # Check image ID exists
        old = self.get(data["id"])
        if not old:
            raise ValueError(f"Cannot find image with ID '{data['id']}'.")

        # Get existing data and check for changes
        if data["tags"] != old["tags"] or data["remark"] != old["remark"]:

            # Update image data
            data["updated"] = dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            data["path"] = old["path"]

            idx = self._get_index(data["id"])
            self._images.update(pd.DataFrame(data, index=[idx]))

            # Store updated record in database
            self._write_database(data)

    def dump_data(self):
        """Returns tag data as a pandas DataFrame."""

        return self._images.dropna(subset=["updated"])

    @staticmethod
    def _hash(filepath):
        """
        Creates an MD5 hash for a file path.

        Parameters
        ----------
        filepath : str
            File path as a string.

        Returns
        -------
        str
            MD5 hash as a string value.
        """

        m = hashlib.md5(filepath.encode("utf-8"))
        return m.hexdigest()

    def _write_database(self, data):
        """
        Writes image tag data to the database.

        Parameters
        ----------
        data : dict
            Tagging data, should contain keys 'id', 'path', 'tags',
            'remark', 'updated'. All values should be provided as
            string values.
        """

        required = "id", "path", "tags", "remark", "updated"
        missing = set(required) - set(data)
        if missing:
            raise KeyError(
                "Missing the following keys from tag data: " + ", ".join(missing)
            )

        self._db.query(
            """
            INSERT INTO tags (id, path, tags, remark, updated)
                VALUES(:id, :path, :tags, :remark, :updated)
            ON CONFLICT (id) DO UPDATE SET
                tags=excluded.tags,
                remark=excluded.remark,
                updated=excluded.updated
            ;
            """,
            data,
        )

    def _initialize_database(self):
        """Creates the tag table if it does not exists."""

        self._db.query(
            """
            CREATE TABLE IF NOT EXISTS tags (
                id TEXT PRIMARY KEY,
                path TEXT UNIQUE NOT NULL,
                tags TEXT,
                remark TEXT,
                updated DATETIME
            );
        """
        )
