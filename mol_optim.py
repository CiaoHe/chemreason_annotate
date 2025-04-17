import json
from rdkit import Chem
from rdkit.Chem import Draw
import gradio as gr
import os
import argparse

class MoleculeAnnotationSystem:
    def __init__(self, data, save_path):
        self.data = data
        self.save_path = save_path
        self.total_entity = data.get('total_entity', 0)
        self.error_entity = data.get('error_entity', 0)
        self.load_cot_result()
        
    def load_cot_result(self):
        cot_result = self.data.get('cot_result', {})
        if isinstance(cot_result, str):
            try:
                self.cot_result = json.loads(cot_result)
            except json.JSONDecodeError:
                self.cot_result = {"error": "Invalid JSON format"}
        else:
            self.cot_result = cot_result
            
    def get_mol_images(self):
        src_mol = Chem.MolFromSmiles(self.data['src'])
        tgt_mol = Chem.MolFromSmiles(self.data['tgt'])
        return (
            Draw.MolToImage(src_mol, size=(400, 300)),
            Draw.MolToImage(tgt_mol, size=(400, 300)),
            self.data['src'],
            self.data['tgt']
        )

def create_interface(data_list, bench_name):
    # Initialize state components
    current_idx = gr.State(0)
    data_list_state = gr.State(data_list)
    
    # Get initial cot keys
    initial_cot_keys = list(json.loads(data_list[0].get('cot_result', '{}')).keys())
    
    with gr.Blocks() as interface:
        # State variables
        current_idx = gr.State(0)
        data_list_state = gr.State(data_list)
        
        # UI components
        with gr.Row():
            src_image = gr.Image(label="Source Molecule")
            src_text = gr.Text(label="Source SMILES")
            tgt_image = gr.Image(label="Target Molecule")
            tgt_text = gr.Text(label="Target SMILES")
        
        with gr.Row():
            total_entity = gr.Number(label="Total Entities")
            error_entity = gr.Number(label="Error Entities")
        
        cot_inputs = []
        for key in initial_cot_keys:
            cot_inputs.append(gr.Textbox(label=key, lines=3))
        
        status_output = gr.Text(label="Status")

        # Navigation buttons
        with gr.Row():
            prev_btn = gr.Button("Previous")
            save_btn = gr.Button("Save Changes")
            next_btn = gr.Button("Next")

        def load_data(current_idx, data_list):
            data = data_list[current_idx]
            save_path = os.path.join(args.output_dir, f"{bench_name}_{current_idx}.json")
            system = MoleculeAnnotationSystem(data, save_path)
            
            src_img, tgt_img, src_smiles, tgt_smiles = system.get_mol_images()
            cot_values = [str(system.cot_result.get(k, "")) for k in initial_cot_keys]
            
            return [
                src_img, src_smiles, 
                tgt_img, tgt_smiles,
                system.total_entity,
                system.error_entity
            ] + cot_values

        def update_idx(change, current_idx, data_list):
            new_idx = current_idx + change
            if 0 <= new_idx < len(data_list):
                return new_idx, *load_data(new_idx, data_list)
            return current_idx, *load_data(current_idx, data_list)

        # Event handlers
        prev_btn.click(
            fn=lambda x, d: update_idx(-1, x, d),
            inputs=[current_idx, data_list_state],
            outputs=[current_idx, src_image, src_text, tgt_image, tgt_text, total_entity, error_entity] + cot_inputs
        )
        
        next_btn.click(
            fn=lambda x, d: update_idx(1, x, d),
            inputs=[current_idx, data_list_state],
            outputs=[current_idx, src_image, src_text, tgt_image, tgt_text, total_entity, error_entity] + cot_inputs
        )

        def save_data(current_idx, data_list, total_ent, error_ent, *cot_values):
            # Create MoleculeAnnotationSystem instance
            data = data_list[current_idx]
            save_path = os.path.join(args.output_dir, f"{bench_name}_{current_idx}.json")
            system = MoleculeAnnotationSystem(data, save_path)
            
            # Update values
            system.total_entity = total_ent
            system.error_entity = error_ent
            system.data.update({
                'total_entity': total_ent,
                'error_entity': error_ent,
                'cot_result': json.dumps(dict(zip(initial_cot_keys, cot_values)), indent=4)
            })
            
            # Save individual file
            with open(save_path, 'w') as f:
                json.dump(system.data, f, indent=4)
            
            # Update data list and save main file
            new_data_list = data_list.copy()
            new_data_list[current_idx] = system.data
            # with open(args.data_path, 'w') as f:
            #     json.dump(new_data_list, f, indent=4)
            
            return "Changes saved successfully!", new_data_list

        save_btn.click(
            fn=save_data,
            inputs=[current_idx, data_list_state, total_entity, error_entity] + cot_inputs,
            outputs=[status_output, data_list_state]
        )
        
        # Load initial data
        interface.load(
            fn=lambda: load_data(0, data_list),
            outputs=[src_image, src_text, tgt_image, tgt_text, total_entity, error_entity] + cot_inputs
        )

    return interface

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_path", type=str, help="Path to input JSON file", default="gsk_hard_cot.json")
    parser.add_argument("--output_dir", type=str, default="annotated_data", help="Output directory for annotated files")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    bench_name = os.path.basename(args.data_path).split('.')[0]
    
    with open(args.data_path) as f:
        data_list = json.load(f)
    
    interface = create_interface(data_list, bench_name)
    interface.launch()