import datetime
from typing import List, Union

from nextcord import PermissionOverwrite, Role, TextChannel


def get_permissions(state: bool):
    permission_overwrites = PermissionOverwrite()
    permission_overwrites.send_messages = state  # noqa
    permission_overwrites.view_channel = True  # noqa

    return permission_overwrites


def get_roles_array(roles: Union[Role, List[Role]]):
    if isinstance(roles, Role):
        return [roles]

    return roles


async def unlockdown(channel: TextChannel, roles: Union[Role, List[Role]]):
    for role in get_roles_array(roles):
        await channel.set_permissions(
            target=role, overwrite=get_permissions(state=True)
        )


async def lockdown(channel: TextChannel, roles: Union[Role, List[Role]]):
    for role in get_roles_array(roles):
        await channel.set_permissions(
            target=role, overwrite=get_permissions(state=False)
        )


def get_week():
    return datetime.datetime.now().isocalendar()[1]
