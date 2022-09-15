import argparse
from blue_sbc.screen.display import instance as display
from . import *
from abcli import logging
import logging

logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser(NAME)
parser.add_argument(
    "task",
    type=str,
    default="",
    help="capture|preview",
)
parser.add_argument(
    "--filename",
    default="",
    type=str,
)
parser.add_argument(
    "--output_path",
    type=str,
    default="",
)
args = parser.parse_args()

success = False
if args.task == "capture":
    success, _, _ = instance.capture(
        filename=os.path.join(args.output_path, "camera.jpg"),
    )
elif args.task == "preview":
    display.sign_images = False
    try:
        while not display.pressed("qe"):
            _, image = instance.capture()
            display.show(image)

        success = True
    finally:
        pass
else:
    logger.error(f"-{NAME}: {args.task}: command not found.")

if not success:
    logger.error(f"-{NAME}: {args.task}: failed.")
