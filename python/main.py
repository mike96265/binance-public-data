import os
import sys


def main():
    print(" ".join(sys.argv))
    print(os.environ["AWS_ACCESS_KEY_ID"])
    print(os.environ["AWS_SECRET_ACCESS_KEY"])


if __name__ == '__main__':
    main()
