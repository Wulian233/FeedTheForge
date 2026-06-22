from server_installer.maven_artifact import MavenArtifact
from storage.file_entry import FileEntry
from storage.repo_type import RepoType


class MavenFileEntry(FileEntry):
    def __init__(self, artifact):
        self.artifact = (
            artifact if isinstance(artifact, MavenArtifact) else MavenArtifact(artifact)
        )
        super().__init__(RepoType.MAVEN_ARTIFACT, self.artifact.file_path)

    def with_maven_repo(self, repo_url):
        self.set_downloadable(
            self.artifact.file_name,
            [f"{repo_url.rstrip('/')}/{self.artifact.url_path}"],
        )
        return self

    def with_maven_url(self, *urls):
        self.set_downloadable(self.artifact.file_name, [url for url in urls if url])
        return self

    def with_maven_base_archive_entry_name(self, base_entry_name="libraries"):
        self.with_archive_entry_name(base_entry_name, self.artifact.url_path)
        return self
