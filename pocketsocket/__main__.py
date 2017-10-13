import sys
import pocketsocket.options

def main(args=None):
    """The main routine."""
    if args is None:
        args = sys.argv[1:]

    print("main routine.", args)


if __name__ == "__main__":
    main()
