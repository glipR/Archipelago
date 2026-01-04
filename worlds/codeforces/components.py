from worlds.LauncherComponents import Component, Type, components, launch


def run_client(*args: str) -> None:
    # Lazy load client.
    from .client.launch import launch_codeforces_client

    launch(launch_codeforces_client, name="Codeforces Client", args=args)


components.append(
    Component(
        "Codeforces Client",
        func=run_client,
        game_name="Codeforces",
        component_type=Type.CLIENT,
        supports_uri=True,
    )
)
