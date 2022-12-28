import argparse
import time
from . import *
from .classes import Sparkfun_Top_phat
from matplotlib import cm
from abcli import logging
import logging

logger = logging.getLogger(__name__)


parser = argparse.ArgumentParser(NAME)
parser.add_argument(
    "task",
    type=str,
    default="",
    help="validate_leds",
)
args = parser.parse_args()

hardware = Sparkfun_Top_phat()

success = False
if args.task == "validate_leds":
    # https://matplotlib.org/3.1.1/tutorials/colors/colormap-manipulation.html
    # https://matplotlib.org/stable/tutorials/colors/colormaps.html

    colormap = cm.get_cmap("GnBu", hardware.pixel_count)(range(hardware.pixel_count))

    logger.info("loop started (Ctrl+C to stop)")
    offset = 0
    # https://stackoverflow.com/a/18994932/10917551
    try:
        while True:
            for index in range(hardware.pixel_count):
                hardware.pixels[index] = tuple(
                    int(thing * 128)
                    for thing in colormap[(index + offset) % hardware.pixel_count][:3]
                )

            offset += 1

            hardware.pixels.show()
            time.sleep(0.1)
    except KeyboardInterrupt:
        logger.info("Ctrl+C, stopping.")
    finally:
        hardware.release()
    success = True
else:
    logger.error(f"-{NAME}: {args.task}: command not found.")

if not success:
    logger.error(f"-{NAME}: {args.task}: failed.")
