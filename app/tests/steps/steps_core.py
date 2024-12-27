from typing import TypeVar

from injector import Injector

from app.app import create_app
from app.utils import create_modules


def prepare_injector(modules=None):
    def step(context):
        mod_default = create_modules()
        modules_final = mod_default + (modules or [])
        context.injector = Injector(modules=modules_final)

    return step


def prepare_api_server():
    def step(context):
        context.app = create_app(injector=context.injector)

    return step


C = TypeVar("C")
