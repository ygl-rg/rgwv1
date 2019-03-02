import sys


if __name__ == "__main__":
    args = sys.argv
    if args[1] == 'rgw_node':
        import rgw_go
        rgw_go.main()
    elif args[1] == 'rgw_init':
        import init_rgw_go
        init_rgw_go.main()
    else:
        print("process type missing")

