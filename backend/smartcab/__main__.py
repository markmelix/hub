import os
import logging
import smartcab
import multiprocessing

import gunicorn.app.base
from smartcab import PROD
from smartcab.data import db
from threading import Thread
from smartcab.interface import mqtt
from dotenv import find_dotenv, load_dotenv
from smartcab.interface.mqtt import MQTTC, MQTTConnectionError


class WSGIApplication(gunicorn.app.base.BaseApplication):
    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self):
        config = {
            key: value
            for key, value in self.options.items()
            if key in self.cfg.settings and value is not None
        }
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application


def main() -> None:
    load_dotenv(find_dotenv())

    logging.getLogger().setLevel(logging.DEBUG)

    db.global_init()

    try:
        mqtt.init()
    except MQTTConnectionError as e:
        logging.error(
            f"Failed to connect to MQTT-broker: {e}. MQTT related queries won't be processed"
        )

    mqttct = Thread(target=MQTTC.loop_forever)
    mqttct.daemon = True
    mqttct.start()

    WORKERS = (multiprocessing.cpu_count() * 2) + 1

    app = smartcab.make_app()

    if PROD:
        logging.info("Running in production-mode - gunicorn server will be used")
        WSGIApplication(
            app,
            {
                "bind": f"0.0.0.0:5000",
                "workers": WORKERS,
            },
        ).run()
    else:
        logging.info("Running in development-mode - flask standard server will be used")
        app.run(host="0.0.0.0", port=5000, debug=True)


if __name__ == "__main__":
    main()
