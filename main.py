from logger import get_logger

logger = get_logger(__name__)


def main():

    logger.info("GNSS-IR Soil Moisture System Started")

    logger.info("Configuration loaded successfully")

    logger.info("Waiting for processing...")


if __name__ == "__main__":
    main()