from api.base_api_client import BaseApiClient


class AzulApiClient(BaseApiClient):
    base_url = "https://api.azul.com/metadata/v1/"

    def packages(self, java_version, os_name, arch, archive_type, package_type):
        return self.get_json(
            "zulu/packages/",
            params={
                "java_version": java_version,
                "os": os_name,
                "arch": arch,
                "archive_type": archive_type,
                "java_package_type": package_type,
                "javafx_bundled": "false",
                "release_status": "ga",
                "availability_types": "CA",
                "page": 1,
                "page_size": 5,
            },
        )
