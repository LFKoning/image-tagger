"""Module containing the Flask tagging server."""

import io
import os
import argparse
import webbrowser

from flask import Flask, render_template, request, redirect, send_file, Response

from config import ConfigReader
from images import Images


class TagServer:
    """
    Flask server for tagging images.

    Parameters
    ----------
    config_file : str
        Path the YAML configuration file.

    Methods
    -------
    start()
        Starts the Flask server.
    """

    def __init__(self, config_file):

        # Set up config and image services
        self._config = ConfigReader(config_file)
        self._images = Images(self._config)

        # Create Flask app and define routes
        self._app = Flask(__name__, static_url_path="/static")
        self._app.add_url_rule("/", "index", self.show_index)
        self._app.add_url_rule("/show_image", "show_image", self.show_image)
        self._app.add_url_rule("/image_tags.csv", "download_tags", self.download_tags)
        self._app.add_url_rule(
            "/store_tags", "store_tags", self.store_tags, methods=["POST"]
        )

    def start(self):
        """Starts the Flask server with the configured host settings."""

        # Get config settings
        host = self._config.get("server/host", "127.0.0.1")
        port = self._config.get("server/port", "8080")
        debug = self._config.get("server/debug mode", False)
        host_str = f"http://{host}:{port}/"

        # The reloader has not yet run - open the browser
        if not os.environ.get("WERKZEUG_RUN_MAIN"):
            webbrowser.open_new(host_str)

        # Run Flask app
        self._app.run(host=host, port=port, debug=debug)

    def show_index(self):
        """Routing: Show the main page."""

        image_id = request.args.get("image_id")
        if not image_id:
            untagged = self._images.first_untagged_id()
            return redirect(f"/?image_id={untagged}")
        else:
            content = self._render_image(image_id)

        metadata = {
            "max_image_width": self._config.get("interface/max_width", 600),
            "max_image_height": self._config.get("interface/max_height", 700),
        }
        return render_template("index.html", content=content, meta=metadata)

    def show_image(self):
        """Routing: Sends the image file to the webbrowser."""

        image_id = request.args.get("image_id")
        image = self._images.get(image_id)

        return send_file(image["path"], mimetype="image/jpg")

    def store_tags(self):
        """Routing: Stores the (updated) tag data for the image."""

        # Get form data
        sep = self._config.get("tagging/multi-separator", ", ")
        data = {
            "id": request.form.get("id"),
            "tags": sep.join(request.form.getlist("tags")),
            "remark": request.form.get("remark").strip(),
        }
        self._images.store(data)

        next_image = self._images.next_id(data["id"])
        target = "/"
        if next_image:
            target = f"/?image_id={next_image}"
        return redirect(location=target)

    def download_tags(self):
        """Routing: Download tag information as CSV file."""

        tags = self._images.dump_data()

        # Use StringIO to capture the to_csv() output
        csv_string = io.StringIO()
        tags.to_csv(csv_string, index=False)
        return Response(csv_string.getvalue(), mimetype="text/csv")

    def _render_image(self, image_id):
        """
        Renders image template for the provided image ID.

        Parameters
        ----------
        image_id : str
            MD5 hash for the image to render.
        """

        # Load all available tags from cofniguration
        shortcuts = self._config.get("tagging/tags")
        if not shortcuts:
            raise ValueError("Could not read any tags from the configuration file.")

        # Load and preprocess the data
        data = self._images.get(image_id)
        if not data:
            raise RuntimeError(f"Cannot render image with ID '{image_id}'.")
        if not isinstance(data["remark"], str):
            data["remark"] = ""

        # Split multiple tags
        if isinstance(data["tags"], str):
            sep = self._config.get("tagging/multi-separator", ", ")
            data["tags"] = data["tags"].split(sep)
        else:
            data["tags"] = []

        # Get next and previous IDs
        data["prev_image_id"] = self._images.prev_id(image_id)
        data["next_image_id"] = self._images.next_id(image_id)

        # Add meta data
        data["all_tags"] = list(shortcuts)
        data["shortcuts"] = shortcuts
        data["tag_question"] = self._config.get("tagging/tag question", "Select tags:")
        data["allow_remarks"] = self._config.get("tagging/allow remarks", False)
        data["multi_select"] = self._config.get("tagging/multi-select", False)

        return render_template("tag_image.html", **data)


if __name__ == "__main__":

    # Get config file from command line
    parser = argparse.ArgumentParser("Tagging server command line interface.")
    parser.add_argument(
        "-c",
        "--config",
        dest="config_file",
        help="Path to the configuration file",
        default="config.yaml",
    )
    args = parser.parse_args()

    server = TagServer(args.config_file)
    server.start()
