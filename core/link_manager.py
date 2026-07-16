from uuid import uuid4


class LinkManager:

    @staticmethod
    def link(video_clip, audio_clip):
        """
        Creates a relationship between video and audio clips.
        """

        link_id = str(uuid4())

        video_clip.linked_id = link_id
        audio_clip.linked_id = link_id

        return True


    @staticmethod
    def unlink(clip, other_clip=None):
        """
        Removes link relationship.
        """

        clip.linked_id = None

        if other_clip is not None:
            other_clip.linked_id = None

        return True


    @staticmethod
    def is_linked(clip):
        return clip.linked_id is not None


    @staticmethod
    def same_link(clip_a, clip_b):
        if (
            clip_a.linked_id is None
            or clip_b.linked_id is None
        ):
            return False

        return clip_a.linked_id == clip_b.linked_id
