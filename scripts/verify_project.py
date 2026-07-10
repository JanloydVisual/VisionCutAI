from core.project import Project
from core.project_importer import ProjectImporter

project = Project()
importer = ProjectImporter(project)

info = importer.import_video("C:/Users/loyde/Downloads/Are all female realtors this desperate https___t.co_93Z8XKmRhw.mp4")

print("Assets :", len(project.assets.all()))
print("Clips  :", len(project.timeline.clips))
print(project.assets.all()[0])
print(project.timeline.clips[0])
