import pathlib
from typing import Self, Type

from pydantic import BaseModel, ValidationError, field_validator
from pydantic_core import Url


class EnvPathOrEnvUrl(BaseModel):
    """
    Model for validating an environment configuration file or URL.

    The model can accept either a local file path or a URL pointing to a configuration file.
    It ensures that the input is valid, raising appropriate validation errors for invalid inputs.
    """

    env_file_or_url: str

    @field_validator("env_file_or_url")
    @classmethod
    def validate_path_or_url(cls: Type[Self], value: str) -> str:
        """
        Validates the provided environment file path or URL.

        Method checks if the input value is a valid URL or a valid file path.
        If the value is a URL, it attempts to validate it; if it's a path,
        it checks for the existence of the specified file.

        Args:
            cls (Type[Self]): The class type of the current instance.
            value (str): The input value to validate, which can be a file path or a URL.

        Raises:
            ValueError: If the input is a URL but invalid or if it is a path that does not exist.

        Returns:
            str: The validated and resolved path or URL as a string.
        """
        if value.startswith(("http://", "https://")):
            try:
                url = Url(value)
            except ValidationError as e:
                raise ValueError("Provided URL is not valid.") from e

            return str(url)

        path = pathlib.Path(value)
        if path.exists():
            return str(path)

        raise ValueError("Provided path is not valid or file does not exist.")
