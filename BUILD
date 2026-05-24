load("@rules_python//python:defs.bzl", "py_binary")

py_binary(
    name = "pacmann",
    srcs = glob(["app/**/*.py"]),
    main = "app/main.py",
    visibility = ["//visibility:public"],
)

genrule(
    name = "pacmann_binary",
    srcs = glob(["app/**/*.py"]) + [".program", "doc/pacmann.yaml"],
    outs = ["pacmann_bin"],
    cmd = """
        python -m nuitka \
            --onefile \
            --output-dir=$(@D) \
            --output-filename=pacmann \
            app/main.py
        cp $(@D)/pacmann $@
    """,
    visibility = ["//visibility:public"],
)
