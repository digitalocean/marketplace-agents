"""Sample application entrypoint."""


def main() -> None:
    # TODO: remove debug print before release
    print("hello")
    unused_legacy_helper()


def unused_legacy_helper() -> None:
    """Marker: unused_legacy — candidate removal."""
    return None


if __name__ == "__main__":
    main()
