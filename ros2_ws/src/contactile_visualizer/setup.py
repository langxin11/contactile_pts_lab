from setuptools import find_packages, setup

package_name = "contactile_visualizer"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/launch", ["launch/visualizer.launch.py"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="xiaodalaing",
    maintainer_email="xiaodalaing@example.com",
    description="Realtime Contactile PTS tactile sensor visualizer.",
    license="TODO: License declaration",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "tactile_gui = contactile_visualizer.app:cli",
        ],
    },
)
