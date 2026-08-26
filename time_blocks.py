"""Build the 28 daytime blocks and the single overnight block."""

from datetime import datetime, timedelta


class TimeBlockModel:
    """Makes the configured daytime and overnight time blocks."""

    def __init__(self, config):
        self.config = config

    def build(self):
        blocks = []

        # Start at 09:00. Move forward 30 minutes at a time.
        current = datetime.strptime(self.config["experiment"]["day_start"], "%H:%M")
        finish = datetime.strptime(self.config["experiment"]["day_end"], "%H:%M")
        minutes = self.config["experiment"]["daytime_period_minutes"]

        block_number = 0
        while current < finish:
            blocks.append({
                "block": block_number,
                "time": current.strftime("%H:%M"),
                "hours": minutes / 60,
                "is_overnight": False,
            })
            current = current + timedelta(minutes=minutes)
            block_number += 1

        # Treat 23:00 to 09:00 as one combined overnight block.
        blocks.append({
            "block": block_number,
            "time": "23:00-09:00",
            "hours": self.config["experiment"]["overnight_period_hours"],
            "is_overnight": True,
        })

        return blocks
