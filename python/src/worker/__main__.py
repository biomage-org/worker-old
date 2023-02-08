import datetime
import time
from logging import INFO, basicConfig, info



from .config import config
from .consume_message import consume
from .response import Response
from .tasks.factory import TaskFactory

# configure logging
basicConfig(format="%(asctime)s %(message)s", level=INFO)


def main():
    if config.IGNORE_TIMEOUT:
        info("Worker configured to ignore timeout, will run forever...")

    while not config.EXPERIMENT_ID:
        info("Experiment not yet assigned, waiting...")
        time.sleep(5)

    last_activity = datetime.datetime.utcnow()
    task_factory = TaskFactory()
    info(
        f"Now listening for experiment {config.EXPERIMENT_ID}, waiting for work to do..."
    )

    job_done = False
    while (
        datetime.datetime.utcnow() - last_activity
    ).total_seconds() <= config.TIMEOUT or config.IGNORE_TIMEOUT and not job_done:

        request = consume()
        if request:
            result = task_factory.submit(request)

            response = Response(request, result)
            response.publish()

            last_activity = datetime.datetime.utcnow()
            job_done = True


    if job_done: info(f"Job done at {last_activity}")
    else: info("Timeout exceeded, shutting down...")


main()
