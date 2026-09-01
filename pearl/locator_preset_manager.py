import json
import os


class LocatorPresetManager(object):

    FILE_NAME = "locator_presets.json"

    LEGACY_ROTATION_KEYS = [
        "wrist_rotation",
        "index_rotation",
        "middle_rotation",
        "ring_rotation",
        "pinkie_rotation",
        "thumb_rotation",
    ]

    LEGACY_FINGER_DRIVER_KEYS = [
        "index_03",
        "middle_03",
        "ring_03",
        "pinkie_03",
        "thumb_03",
    ]

    @classmethod
    def get_preset_path(cls):

        current_dir = os.path.dirname(__file__)
        data_dir = os.path.join(current_dir, "data")

        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        return os.path.join(data_dir, cls.FILE_NAME)

    @classmethod
    def load_all_presets(cls):

        path = cls.get_preset_path()

        if not os.path.exists(path):
            return {}

        try:
            with open(path, "r") as f:
                return json.load(f)

        except (json.JSONDecodeError, OSError) as error:
            print(
                "Could not load locator presets from '{}': {}".format(
                    path,
                    error,
                )
            )
            return {}

    @classmethod
    def save_all_presets(cls, data):

        path = cls.get_preset_path()
        temp_path = "{}.tmp".format(path)

        try:
            with open(temp_path, "w") as f:
                json.dump(
                    data,
                    f,
                    indent=4,
                )

            os.replace(
                temp_path,
                path,
            )

        except OSError:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

            raise

    @classmethod
    def load_preset(cls, module_name, preset_name):

        data = cls.load_all_presets()

        return data.get(
            module_name,
            {},
        ).get(
            preset_name
        )

    @classmethod
    def save_preset(
        cls,
        module_name,
        preset_name,
        positions,
    ):

        data = cls.load_all_presets()

        if module_name not in data:
            data[module_name] = {}

        data[module_name][preset_name] = positions

        cls.save_all_presets(data)

    @classmethod
    def delete_preset(
        cls,
        module_name,
        preset_name,
    ):

        data = cls.load_all_presets()

        if module_name not in data:
            return False

        if preset_name not in data[module_name]:
            return False

        del data[module_name][preset_name]

        cls.save_all_presets(data)

        return True

    @classmethod
    def delete_module(
        cls,
        module_name,
    ):

        data = cls.load_all_presets()

        if module_name not in data:
            return False

        del data[module_name]

        cls.save_all_presets(data)

        return True

    @classmethod
    def convert_pose_to_new_format(
        cls,
        module_name,
        preset_name,
    ):

        data = cls.load_all_presets()

        if module_name not in data:
            return False

        if preset_name not in data[module_name]:
            return False

        old_pose = data[module_name][preset_name]
        new_pose = {}

        for key, value in old_pose.items():

            if key == "metadata":
                new_pose[key] = value
                continue

            if key in cls.LEGACY_ROTATION_KEYS:
                new_pose[key] = value
                continue

            if (
                isinstance(value, dict)
                and "offset" in value
                and "ctrl" in value
            ):
                converted_value = {
                    "offset": dict(
                        value.get("offset") or {}
                    ),
                    "ctrl": dict(
                        value.get("ctrl") or {}
                    ),
                }

                converted_value["ctrl"].setdefault(
                    "custom_rotation",
                    None,
                )

                new_pose[key] = converted_value
                continue

            if isinstance(value, dict):

                translate = value.get(
                    "translation",
                    [0, 0, 0],
                )

                offset_rotate = value.get(
                    "offset_rotation",
                    [0, 0, 0],
                )

                ctrl_rotate = value.get(
                    "ctrl_rotation",
                    [0, 0, 0],
                )

                ctrl_translate = value.get(
                    "ctrl_translation",
                    [0, 0, 0],
                )

            else:

                translate = value
                offset_rotate = [0, 0, 0]
                ctrl_rotate = [0, 0, 0]
                ctrl_translate = [0, 0, 0]

            new_pose[key] = {
                "offset": {
                    "translate": translate,
                    "rotate": offset_rotate,
                },
                "ctrl": {
                    "translate": ctrl_translate,
                    "rotate": ctrl_rotate,
                    "custom_rotation": None,
                },
            }

        data[module_name][preset_name] = new_pose

        cls.save_all_presets(data)

        return True

    @classmethod
    def add_rotation_presets_to_pose(
        cls,
        module_name,
        preset_name,
    ):

        data = cls.load_all_presets()

        if module_name not in data:
            return False

        if preset_name not in data[module_name]:
            return False

        pose = data[module_name][preset_name]

        for key in cls.LEGACY_ROTATION_KEYS:

            if key not in pose:
                pose[key] = 0.0

        cls.save_all_presets(data)

        return True

    @classmethod
    def add_finger_up_references_to_pose(
        cls,
        module_name,
        preset_name,
        finger_positions,
    ):

        data = cls.load_all_presets()

        if module_name not in data:
            return False

        if preset_name not in data[module_name]:
            return False

        pose = data[module_name][preset_name]

        metadata = pose.setdefault(
            "metadata",
            {},
        )

        finger_up_references = metadata.setdefault(
            "finger_up_references",
            {},
        )

        for finger, world_position in finger_positions.items():

            finger_up_references[finger] = {
                "world_translate": list(
                    world_position
                )
            }

        cls.save_all_presets(data)

        return True

    @classmethod
    def migrate_finger_driver_rotations(
        cls,
        module_name,
        preset_name,
        driver_keys=None,
    ):

        data = cls.load_all_presets()

        if module_name not in data:
            return False

        if preset_name not in data[module_name]:
            return False

        pose = data[module_name][preset_name]

        metadata = pose.get("metadata") or {}

        orientation = metadata.get(
            "orientation",
            "x",
        ).lower()

        axis_indices = {
            "x": 0,
            "y": 1,
            "z": 2,
        }

        rotation_index = axis_indices.get(
            orientation,
            0,
        )

        if driver_keys is None:
            driver_keys = cls.LEGACY_FINGER_DRIVER_KEYS

        driver_keys = set(driver_keys)

        for key, value in pose.items():

            if not isinstance(value, dict):
                continue

            ctrl_data = value.get("ctrl")

            if not isinstance(ctrl_data, dict):
                continue

            ctrl_data.setdefault(
                "custom_rotation",
                None,
            )

            if key not in driver_keys:
                continue

            ctrl_rotate = ctrl_data.get(
                "rotate"
            ) or [0, 0, 0]

            custom_rotation = 0.0

            if len(ctrl_rotate) > rotation_index:
                custom_rotation = ctrl_rotate[
                    rotation_index
                ]

            ctrl_data["custom_rotation"] = (
                custom_rotation
            )

            ctrl_data["rotate"] = [
                0.0,
                0.0,
                0.0,
            ]

        cls.save_all_presets(data)

        return True