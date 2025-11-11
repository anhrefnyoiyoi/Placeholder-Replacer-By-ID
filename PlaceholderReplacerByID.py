# PlaceholderReplacerByID.py
import re
import ast

class PlaceholderReplacerByID:
    """
    A versatile ComfyUI custom node for dynamic prompt workflows.
    
    This node processes a list of prompt templates (split by a customizable delimiter) and corresponding artist ID sequences.
    It replaces a specified placeholder token (e.g., '[a1]') in each template with the artist name mapped to the first ID in each sequence.
    Supports flexible slot handling (scales to any number of prompts/IDs), with options to mirror the first prompt across all slots,
    auto-increment IDs from a base value, or manually override IDs. Ideal for batch-generating prompts with varied artist styles.
    
    Inputs: ID sequences, prompt list, artist mappings, toggles for behavior, and customization options.
    Outputs: Resolved prompts (joined by ';;;;;'), debug information, and primary artist IDs with names.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                # Single INT_LIST input, will be split into slots based on num prompts
                "id_sequences": ("INT_LIST", {"forceInput": True}),

                # Prompt templates (delimited by prompt_delimiter)
                "prompt_list": ("STRING", {"forceInput": True}),

                # Lines "1_artistName"
                "string_list": ("STRING", {"forceInput": True}),

                # Behavior toggles
                "mirror_first_prompt": ("BOOLEAN", {"default": False, "label": "Mirror First Prompt Across All"}),
                "auto_step_ids": ("BOOLEAN", {"default": False, "label": "Auto-Step IDs"}),
                "manual_ids": ("BOOLEAN", {"default": False, "label": "Use Manual IDs"}),

                # Manual override: delimited list of IDs
                "manual_ids_list": ("STRING", {"forceInput": True}),

                # Input-only integer
                "increment_base": ("INT", {"forceInput": True}),

                # Literal placeholder the user wants to replace
                "placeholder_token": ("STRING", {
                    "default": "[a1]",
                    "label": "Literal Placeholder Token"
                }),

                # Delimiter for splitting prompt_list
                "prompt_delimiter": ("STRING", {
                    "default": ";;;;;",
                    "label": "Prompt Delimiter"
                }),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("resolved_prompts", "debug_info", "primary_ids")
    FUNCTION = "process"
    CATEGORY = "Utils"

    # -------------------------
    # Helpers
    # -------------------------
    def parse_list(self, raw):
        if raw is None or raw == "":
            return []
        if isinstance(raw, (list, tuple)):
            out = []
            for x in raw:
                try:
                    out.append(int(x))
                except Exception:
                    pass
            return out
        if isinstance(raw, (int, float)):
            return [int(raw)]
        if isinstance(raw, str):
            s = raw.strip()
            if s.startswith("[") and s.endswith("]"):
                try:
                    parsed = ast.literal_eval(s)
                    if isinstance(parsed, (list, tuple)):
                        return [int(x) for x in parsed if isinstance(x, (int, float)) or (isinstance(x, str) and x.strip().lstrip('-').isdigit())]
                except Exception:
                    pass
            return [int(x) for x in re.split(r"[;,\s]+", s) if x.strip().lstrip('-').isdigit()]
        return []

    def parse_manual_ids(self, raw):
        if not raw:
            return []
        parts = raw.strip().split(";")
        out = []
        for p in parts:
            p = p.strip()
            if p.lstrip("-").isdigit():
                out.append(int(p))
        return out

    # Literal placeholder replacement
    def resolve_string(self, num_list, template, artist_map, placeholder_token):
        if not template:
            return template
        if not placeholder_token:
            return template

        if num_list and len(num_list) > 0:
            first_id = num_list[0]
            replacement = artist_map.get(first_id, "")
        else:
            replacement = ""

        # literal replace only
        return template.replace(placeholder_token, replacement)

    # -------------------------
    # Main
    # -------------------------
    def process(self, id_sequences, prompt_list, string_list,
                mirror_first_prompt, auto_step_ids, manual_ids,
                manual_ids_list, increment_base,
                placeholder_token, prompt_delimiter):

        # -----------------------------
        # Split prompt templates
        # -----------------------------
        str_parts = (prompt_list or "").split(prompt_delimiter)
        num_slots = len(str_parts)

        # -----------------------------
        # ID SEQUENCES (single INT_LIST, split into slots)
        # -----------------------------
        seq = self.parse_list(id_sequences)  # Ensure it's a list of ints
        while len(seq) < num_slots:
            seq.append(None)

        id_lists = []
        for i in range(num_slots):
            id_lists.append([seq[i]] if seq[i] is not None else [])

        # -----------------------------
        # Artist map
        # -----------------------------
        artist_map = {}
        for line in (string_list or "").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                num, name = line.split("_", 1)
                artist_map[int(num.strip())] = name.strip()
            except Exception:
                pass

        debug_log = []
        debug_log.append(f"num_slots={num_slots}")
        debug_log.append(f"id_sequences={seq}")
        debug_log.append(f"mirror_first_prompt={mirror_first_prompt}; auto_step_ids={auto_step_ids}; manual_ids={manual_ids}")
        debug_log.append(f"manual_ids_list={manual_ids_list}")

        # -----------------------------
        # Auto-step IDs
        # -----------------------------
        try:
            base = int(increment_base)
        except Exception:
            base = None

        if auto_step_ids and base is not None:
            for i in range(num_slots):
                id_lists[i] = [base + i] + id_lists[i][1:] if id_lists[i] else [base + i]
            debug_log.append(f"auto_step_ids applied with base={base}")

        # -----------------------------
        # Mirror first template
        # -----------------------------
        if mirror_first_prompt and str_parts:
            first_str = str_parts[0]
            str_parts = [first_str] * num_slots

        # -----------------------------
        # Manual IDs override
        # -----------------------------
        forced_vals = self.parse_manual_ids(manual_ids_list)
        if manual_ids and len(forced_vals) >= num_slots:
            for i in range(num_slots):
                id_lists[i] = [forced_vals[i]] + id_lists[i][1:]
            debug_log.append("manual_ids override applied.")

        # -----------------------------
        # Resolve templates (literal placeholder)
        # -----------------------------
        all_results = []
        for i in range(num_slots):
            result = self.resolve_string(id_lists[i], str_parts[i], artist_map, placeholder_token)
            all_results.append(result)

        joined = ";;;;;".join(all_results)

        # -----------------------------
        # Primary ID names
        # -----------------------------
        primary_ids = []
        for lst in id_lists:
            if lst and len(lst) > 0:
                val = lst[0]
                name = artist_map.get(int(val), "NOT FOUND")
                primary_ids.append(f"{val}_{name}")
            else:
                primary_ids.append("NOT FOUND")

        return (joined, "\n".join(debug_log), ";".join(primary_ids))


NODE_CLASS_MAPPINGS = {
    "Placeholder Replacer By ID": PlaceholderReplacerByID
}
