import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()


install_requires = [
    "discord",
    "pydantic>=2.0",
    "pydantic-settings",
]

setuptools.setup(
    name="minecontrol",
    version="0.1.0",
    author="Leo",
    author_email="leocasti2@gmail.com",
    description="Un bot de Discord para iniciar, detener y monitorear un servidor de Minecraft.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/CalumRakk/minecontrol",
    packages=["minecontrol", "minecontrol.discord_bot"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Games/Entertainment :: Real Time Strategy",
        "Framework :: AsyncIO",
    ],
    python_requires=">=3.10.0",
    install_requires=install_requires,
    entry_points={
        "console_scripts": [
            "minecontrol=minecontrol.cli:run",
        ],
    },
)
