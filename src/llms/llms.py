import torch

import sys

from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
)

model_class = {
    "causal_lm": AutoModelForCausalLM,
}

from openai import OpenAI

# sys.path.append("..")

import os

# os.environ["CUDA_VISIBLE_DEVICES"] = "3"

import json

import re

import time

class LLMKernel:
    def __init__(self, kernel_type, max_gpu_memory, eval_device, max_new_tokens=256):
        print("Initialize AIOS powered by LLM: {}".format(kernel_type))
        self.config = self.load_config(kernel_type)
        # self.device_map = {"": int(os.environ.get("LOCAL_RANK") or 0)}
        self.max_gpu_memory = self.convert_map(max_gpu_memory)
        self.eval_device = eval_device

        self.load_llm_and_tokenizer()
        self.MAX_NEW_TOKENS = max_new_tokens
        print("AIOS LLM successfully loaded. ")

    def convert_map(self, map):
        new_map = {}
        for k,v in map.items():
            new_map[int(k)] = v
        return new_map

    def load_config(self, kernel_type):
        # print(os.getcwd())
        config_file = os.path.join(os.getcwd(), "src", "llms", "llm_config/{}.json".format(kernel_type))
        with open(config_file, "r") as f:
            config = json.load(f)
            return config

    def load_llm_and_tokenizer(self): # load model from config
        open_sourced = self.config["open_sourced"]
        self.model_type = self.config["model_type"]
        self.model_name = self.config["model_name"]
        
        if open_sourced:
            hf_token = self.config["hf_token"] if "hf_token" in self.config.keys() else None
            cache_dir = self.config["cache_dir"] if "cache_dir" in self.config.keys() else None
            self.model = model_class[self.model_type].from_pretrained(
                self.model_name,
                use_auth_token = hf_token,
                cache_dir = cache_dir,
                torch_dtype=torch.float16,
                # load_in_8bit = True,
                device_map="auto",
                max_memory = self.max_gpu_memory
            )
            # self.model = self.model.to(self.device)
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                use_auth_token = hf_token,
                cache_dir = cache_dir
            )
        else:
            if self.model_name == "gpt3.5-turbo":
                self.model = OpenAI()
                self.tokenizer = None
            else:
                return NotImplementedError

    def extract_before_parenthesis(s):
        match = re.search(r'^(.*?)\([^)]*\)', s)
        return match.group(1) if match else s
    
    def address_request(self, prompt, temperature=0.0):
        # The pattern looks for 'gpt', 'claude', or 'gemini', ignoring case (re.IGNORECASE)
        closed_model_pattern = r'gpt|claude|gemini'
        # execute_time = time.time()
        # waiting_time = execute_time - start_time
        # print(f"Waiting time: {waiting_time}")
        # Search for the pattern in the text
        if re.search(closed_model_pattern, prompt, re.IGNORECASE):
            return self.closed_llm_process(prompt)
        else:
            return self.open_llm_process(prompt)

    def closed_llm_process(self, prompt):
        return NotImplementedError

    def open_llm_process(self, prompt):
        self.tokenizer.pad_token_id = self.tokenizer.eos_token_id
        input_ids = self.tokenizer.encode(prompt, return_tensors="pt")
        input_ids = input_ids.to(self.eval_device)
        # print("Input ID: ", input_ids)
        # Example 1: Print the scores for each token generated with Greedy Search
        output_ids = self.model.generate(
            input_ids, max_new_tokens = self.MAX_NEW_TOKENS, num_return_sequences=1
        )
        outputs = self.tokenizer.decode(output_ids[0], skip_special_tokens=True)
        # print(outputs)
        outputs = outputs[len(prompt)+1: ]
        return outputs

if __name__ == "__main__":
    llm_type = "gemma-2b-it"
    llm = LLMKernel(llm_type)
    prompt = "Craft a tale about a valiant warrior on a quest to uncover priceless treasures hidden within a mystical island."
    llm.address_request(prompt)
