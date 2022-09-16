import os
import time
from abcli import VERSION
from abcli import file
from abcli import string
from abcli.modules import host
from abcli.modules import terraform
from abcli.modules.cookie import cookie
from abcli.modules import objects
from abcli.plugins import storage
from abcli.plugins.graphics import add_signature
from abcli.plugins.message.messenger import instance as messenger
from abcli.timer import Timer
from . import NAME
from .functions import reply_to_bash
from blue_sbc.algo.diff import Diff
from blue_sbc.hat import hat
from blue_sbc.screen import screen
from blue_sbc.imager import imager
from abcli.logging import crash_report
from abcli import logging
import logging

logger = logging.getLogger(__name__)


class Session(object):
    def __init__(self):
        super(Session, self).__init__()

        self.keys = {
            "e": "exit",
            "r": "reboot",
            "s": "shutdown",
            "u": "update",
        }

        self.diff = Diff(cookie.get("session.imager.diff", 0.1))

        self.capture_requested = False

        self.frame = 0
        self.new_frame = False
        self.frame_image = terraform.poster(None)
        self.frame_filename = ""

        self.auto_upload = cookie.get("session.auto_upload", True)
        self.outbound_queue = cookie.get("session.outbound_queue", "stream")

        self.messages = []

        self.model = None

        self.params = {"iteration": -1}

        self.state = {}

        self.switch_on_time = None

        self.timer = {}
        for name, period in {
            "imager": 60 * 5,
            "messenger": 60,
            "reboot": 60 * 60 * 4,
            "screen": 4,
            "temperature": 300,
        }.items():
            self.add_timer(name, period)

    def add_timer(self, name, period):
        if name not in self.timer:
            period = cookie.get(f"session.{name}.period", period)
            self.timer[name] = Timer(period, name)
            logger.info(
                "{}: timer[{}]:{}".format(
                    NAME,
                    name,
                    string.pretty_frequency(1 / period),
                )
            )
            return True
        return False

    def check_imager(self):
        self.new_frame = False

        if not cookie.get("session.imager.enabled", True):
            return
        if not self.capture_requested and not self.timer["imager"].tick():
            return
        self.capture_requested = False

        success, image = imager.capture()
        if not success:
            return

        hat.pulse(hat.data_pin)

        if not self.diff.same(image):
            return

        self.frame += 1

        image = add_signature(
            image,
            [" | ".join(objects.signature())],
            [" | ".join(host.signature())],
        )

        filename = os.path.join(
            os.getenv("abcli_object_path", ""),
            f"{self.frame:016d}.jpg",
        )

        if not file.save_image(filename, image):
            return

        self.new_frame = True
        self.frame_image = image
        self.frame_filename = filename

        if self.outbound_queue:
            from abcli.plugins.message import Message

            Message(
                filename=self.frame_filename,
                recipient=self.outbound_queue,
                subject="frame",
            ).submit()
        elif self.auto_upload:
            storage.upload_file(self.frame_filename)

    def check_keyboard(self):
        for key in screen.key_buffer:
            if key in self.keys:
                reply_to_bash(self.keys[key])
                return False

        if " " in screen.key_buffer:
            self.capture_requested = True

        screen.key_buffer = []

        return None

    def check_messages(self):
        self.messages = []

        if not self.timer["messenger"].tick():
            return None

        _, self.messages = messenger.request()
        if self.messages:
            hat.pulse(hat.incoming_pin)

        for message in self.messages:
            output = self.process_message(message)
            if output in [True, False]:
                return output

        return None

    def check_seed(self):
        seed_filename = host.get_seed_filename()
        if not file.exist(seed_filename):
            return None

        success, content = file.load_json(file.set_extension(seed_filename, "json"))
        if not success:
            return None

        hat.pulse("outputs")

        seed_version = content.get("version", "")
        if seed_version <= VERSION:
            return None

        logger.info(f"{NAME}: seed {seed_version} detected.")
        reply_to_bash("seed", [seed_filename])
        return False

    def check_switch(self):
        if hat.activated(hat.switch_pin):
            if self.switch_on_time is None:
                self.switch_on_time = time.time()
                logger.info("{NAME}: switch_on_time was set.")
        else:
            self.switch_on_time = None

        if self.switch_on_time is not None:
            hat.pulse("outputs")

            if time.time() - self.switch_on_time > 10:
                reply_to_bash("shutdown")
                return False
            else:
                return True

        return None

    def check_timers(self):
        if self.timer["screen"].tick():
            screen.show(
                image=self.frame_image,
                session=self,
                header=self.signature(),
                sidebar=string.pretty_param(self.params),
            )

        if self.timer["reboot"].tick("wait"):
            reply_to_bash("reboot")
            return False

        if self.timer["temperature"].tick():
            self.read_temperature()

        return None

    def close(self):
        hat.release()
        screen.release()

    def process_message(self, message):
        if (
            cookie.get("session.monitor.enabled", True)
            and message.subject in "bolt,frame".split(",")
            and not host.is_headless()
        ):
            logger.info(f"{NAME}: frame received: {message.as_string()}")
            self.new_frame, self.frame_image = file.load_image(message.filename)

        if message.subject == "capture":
            logger.info(f"{NAME}: capture message received.")
            self.capture_requested = True

        if message.subject in "reboot,shutdown".split(","):
            logger.info(f"{NAME}: {message.subject} message received.")
            reply_to_bash(message.subject)
            return False

        if message.subject == "update":
            try:
                if message.data["version"] > VERSION:
                    reply_to_bash("update")
                    return False
            except:
                crash_report(f"-{NAME}: process_message(): bad update message.")

        return None

    # https://www.cyberciti.biz/faq/linux-find-out-raspberry-pi-gpu-and-arm-cpu-temperature-command/
    def read_temperature(self):
        if not host.is_rpi():
            return

        params = {}

        success, output = file.load_text("/sys/class/thermal/thermal_zone0/temp")
        if success:
            output = [thing for thing in output if thing]
            if output:
                try:
                    params["temperature.cpu"] = float(output[0]) / 1000
                except:
                    crash_report(f"{NAME}: read_temperature(): failed.")
                    return

        self.params.update(params)
        logger.info(
            "{}: {}".format(
                NAME,
                ", ".join(string.pretty_param(params)),
            )
        )

    def signature(self):
        return [
            " | ".join(objects.signature(self.frame)),
            " | ".join(sorted([timer.signature() for timer in self.timer.values()])),
            " | ".join(
                (["*"] if self.new_frame else [])
                + (["^"] if self.auto_upload else [])
                + ([f">{self.outbound_queue}"] if self.outbound_queue else [])
                + ([f"hat:{hat.kind}"] if hat.kind else [])
                + (
                    [
                        "switch:{}".format(
                            string.pretty_duration(
                                time.time() - self.switch_on_time,
                                largest=True,
                                short=True,
                            )
                        )
                    ]
                    if self.switch_on_time is not None
                    else []
                )
                + [
                    "diff: {:.03f} - {}".format(
                        self.diff.last_diff,
                        string.pretty_duration(
                            self.diff.last_same_period,
                            largest=True,
                            include_ms=True,
                            short=True,
                        ),
                    ),
                    string.pretty_shape_of_matrix(self.frame_image),
                ]
                + ([] if self.model is None else self.model.signature())
            ),
        ]

    @staticmethod
    def start():
        success = True
        logger.info(f"{NAME}: started.")

        try:
            session = Session()

            while session.step():
                pass

            logger.info(f"{NAME}: stopped.")
        except KeyboardInterrupt:
            logger.info(f"{NAME}: Ctrl+C: stopped.")
            reply_to_bash("exit")
        except:
            crash_report(f"{NAME} failed.")
            success = False

        try:
            session.close()
        except:
            crash_report(f"-{NAME}: close(): failed.")
            success = False

        return success

    def step(
        self,
        steps="all",
    ):
        """step session.

        Args:
            steps (str, optional): steps. Defaults to "all".

        Returns:
            bool: success.
        """
        if steps == "all":
            steps = "imager,keyboard,messages,seed,switch,timers".split(",")

        self.params["iteration"] += 1

        hat.pulse(hat.looper_pin, 0)

        for enabled, step_ in zip(
            [
                "keyboard" in steps,
                "messages" in steps,
                "timers" in steps,
                "switch" in steps,
                "seed" in steps,
                "imager" in steps,
            ],
            [
                self.check_keyboard,
                self.check_messages,
                self.check_timers,
                self.check_switch,
                self.check_seed,
                self.check_imager,
            ],
        ):
            if not enabled:
                continue
            output = step_()
            if output in [False, True]:
                return output

        return True
