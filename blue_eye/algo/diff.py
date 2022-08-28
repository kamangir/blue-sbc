import cv2
import numpy as np
import time
from . import NAME
from abcli import string
from abcli.logging import crash_report
from abcli import logging
import logging

logger = logging.getLogger(__name__)


class Diff(object):
    def __init__(self, threshold=0.1):
        self.size = (60, 80)
        self.threshold = threshold

        self.last_diff = 0.0
        self.last_same_period = 0.0
        self.last_diff_time = time.time()

        self.previous = None

    def same(self, image):
        if self.threshold < 0:
            return False

        image_scaled = cv2.resize(image, self.size)

        if self.previous is None:
            self.previous = image_scaled
            self.last_diff_time = time.time()

            logger.info(
                f"{NAME}.diff.same({string.pretty_shape_of_matrix(image)}): initialized."
            )
            return False

        try:
            self.last_diff = float(
                np.percentile(
                    np.abs(
                        image_scaled.astype(np.float) - self.previous.astype(np.float)
                    ),
                    90,
                )
                / 255
            )
            is_same = self.last_diff <= self.threshold

            logger.info(
                "{}.diff.same({}): {:.03f} - {}{}".format(
                    NAME,
                    string.pretty_shape_of_matrix(image),
                    self.last_diff,
                    ("!same,same".split(","))[int(is_same)],
                    " - {} since last diff.".format(
                        string.pretty_duration(
                            time.time() - self.last_diff_time,
                            include_ms=True,
                            largest=True,
                            short=True,
                        )
                    ),
                )
            )

            if not is_same:
                self.last_same_period = time.time() - self.last_diff_time
                self.last_diff_time = time.time()

            self.previous = image_scaled

            return is_same
        except:
            crash_report(
                f"{NAME}.diff.same({string.pretty_shape_of_matrix(image)}) failed"
            )

        self.previous = None
        return False
