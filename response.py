from validator_collection import validators, checkers, errors

def main():
    print(validate(input("What's your email address? ")))


def validate(s):
    # for testing:
    # malan at harvard dot edu
    # malan@@@harvard.edu
    try:
        check = validators.email(s)
        if checkers.is_email(check):
            return "Valid"
        raise ValueError
    except ValueError:
        return "Invalid"


if __name__ == "__main__":
    main()
