from pathlib import Path


class MavenArtifact:
    def __init__(self, artifact_id):
        self.id = artifact_id
        raw_id = artifact_id
        if "@" in raw_id:
            raw_id, self.format = raw_id.split("@", 1)
        else:
            self.format = "jar"

        parts = raw_id.split(":")
        self.namespace = parts[0]
        self.name = parts[1]
        self.version = parts[2]
        self.constraint = parts[3] if len(parts) > 3 else None
        if self.constraint:
            self.file_name = (
                f"{self.name}-{self.version}-{self.constraint}.{self.format}"
            )
        else:
            self.file_name = f"{self.name}-{self.version}.{self.format}"

        slices = [*self.namespace.split("."), self.name, self.version, self.file_name]
        self.url_path = "/".join(slices)
        self.file_path = str(Path(*slices))
