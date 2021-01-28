"""Module for loading YAML configuration files."""

import logging
import warnings

import yaml


class ConfigReader:
    """
    Class for loading YAML configuration files.

    Parameters
    ----------
    config_path : str
        Path to the YAML configuration file.
    """

    def __init__(self, config_path):
        self._log = logging.getLogger(__name__)
        self._config = self._load(config_path)

    def _load(self, config_path):
        """
        Loads the configuration as dictionairy.

        Parameters
        ----------
        config_path : str
            Path to the survey data.

        Returns
        -------
        pandas.DataFrame
            Survey data as pandas DataFrame.

        """

        self._log.info("Reading configuration from: %s", config_path)

        try:
            with open(config_path, "r") as config_file:
                config = yaml.safe_load(config_file)

        except IOError:
            msg = f"Cannot read configuration file {config_path}."
            self._log.exception(msg)
            raise RuntimeError(msg)

        self._log.info("Finished reading configuration.")
        return config

    def _check_key(self, config, key, not_found):
        """Checks presence of a key in the configuration."""

        valid = "error", "warn", "silent"
        if not_found not in valid:
            raise ValueError(
                "Unexpected value '%s' for not_found parameter, use one of '%s'." %
                (not_found, "', '".join(valid))
            )

        if key not in config:
            if not_found == "error":
                msg = f"Cannot find key '{key}' in configuration."
                self._log.error(msg)
                raise KeyError(msg)
            elif not_found == "warn":
                msg = f"Cannot find key '{key}' in configuration."
                warnings.warn(msg)
                self._log.warning(msg)
            return False

        return True

    def get(self, path, default=None, not_found="silent"):
        """
        Get a value from the configuration using the specified path.

        Parameters
        ----------
        path : str
            Path to the requested value, for example:
            "some_section/some_key" would retrieve config["some_section"]["some_key"]
        default : Optional[mixed]
            Value to return when the path is not found.
        not_found : Optional[str]
            Specify what to do when a path is not found:
            - silent:  silently return the default value (default)
            - warn:    raise a warning then return default value.
            - error:   raise an error.

        Returns
        -------
        mixed
            The requested value.
        """

        self._log.debug("Getting configuration key: %s", path)

        # Recursively traverse the path
        parent = self._config
        while "/" in path:
            key, path = path.split("/", 1)
            if self._check_key(parent, key, not_found):
                parent = parent[key]
            else:
                return default

        # Return key if it exists
        if self._check_key(parent, path, not_found):
            self._log.debug("Returning configuration value: %s", parent[path])
            return parent[path]

        # Return default otherwise
        self._log.debug("Returning default value: %s", default)
        return default

    def set(self, path, value, not_found="error"):
        """
        Set a configuration key using the specified path and value.

        Parameters
        ----------
        path : str
            Path to the requested value, for example:
            "some_section/some_key" would retrieve config["some_section"]["some_key"]
        value : mixed
            Value to set the key to.
        not_found : Optional[str]
            Specify what to do when a path is not found:
            - error:   raise an error (default).
            - warn:    raise a warning then return default value.
            - silent:  continue silently, leaving the configuration as-is.

        Returns
        -------
        bool
            True on succes, False on error.
        """

        self._log.debug("Setting configuration key: %s", path)

        # Recursively traverse the path
        parent = self._config
        while "/" in path:
            key, path = path.split("/", 1)
            if self._check_key(parent, key, not_found):
                parent = parent[key]
            else:
                return False

        # Set key if it exists
        if self._check_key(parent, path, not_found):
            self._log.debug("Setting value: %s", value)
            parent[path] = value
            return True

        return False
