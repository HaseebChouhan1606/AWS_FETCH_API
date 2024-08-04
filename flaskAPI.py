





import boto3
import face_recognition
import os
import shutil
from flask import Flask, request, jsonify
from botocore.exceptions import NoCredentialsError, PartialCredentialsError

app = Flask(__name__)

# AWS S3 configuration
s3 = boto3.client('s3',
                      aws_access_key_id='AKIAZC6SZP4REQWKCOWD',
                      aws_secret_access_key='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')
bucket_name = 'sharyng-clustered-images'

# Local directory to save matched cluster
local_save_directory = r'C:\Users\Haseeb Chouhan\Desktop\SARAM\Output'

# Create the directory if it doesn't exist
if not os.path.exists(local_save_directory):
    os.makedirs(local_save_directory)

def find_and_download_cluster(reference_image_path):
    reference_image = face_recognition.load_image_file(reference_image_path)
    reference_face_encodings = face_recognition.face_encodings(reference_image)

    if not reference_face_encodings:
        return "No face detected in the reference image.", False
    else:
        reference_face_encoding = reference_face_encodings[0]
        try:
            clusters = s3.list_objects_v2(Bucket=bucket_name, Delimiter='/')
            matched_cluster = None

            for cluster in clusters.get('CommonPrefixes', []):
                cluster_prefix = cluster.get('Prefix')
                cluster_objects = s3.list_objects_v2(Bucket=bucket_name, Prefix=cluster_prefix).get('Contents', [])

                for obj in cluster_objects:
                    if obj['Key'].lower().endswith(('.png', '.jpg', '.jpeg')):
                        s3.download_file(bucket_name, obj['Key'], 'temp_image.jpg')
                        cluster_image = face_recognition.load_image_file('temp_image.jpg')
                        cluster_face_encodings = face_recognition.face_encodings(cluster_image)

                        if cluster_face_encodings:
                            cluster_face_encoding = cluster_face_encodings[0]
                            results = face_recognition.compare_faces([reference_face_encoding], cluster_face_encoding)
                            if results[0]:
                                matched_cluster = cluster_prefix
                            break

                if matched_cluster:
                    break

            if matched_cluster:
                matched_cluster_objects = s3.list_objects_v2(Bucket=bucket_name, Prefix=matched_cluster).get('Contents', [])
                for obj in matched_cluster_objects:
                    if obj['Key'].endswith('/'):
                        continue
                    local_path = os.path.join(local_save_directory, os.path.relpath(obj['Key'], matched_cluster))
                    os.makedirs(os.path.dirname(local_path), exist_ok=True)
                    s3.download_file(bucket_name, obj['Key'], local_path)
                return f"Cluster {matched_cluster} downloaded to {local_save_directory}.", True
            else:
                return "No matching cluster found.", False
        except NoCredentialsError:
            return "AWS credentials not found. Please configure your credentials.", False
        except PartialCredentialsError:
            return "Incomplete AWS credentials found. Please check your credentials.", False
        except Exception as e:
            return f"An error occurred: {e}", False

@app.route('/match_and_download', methods=['POST'])
def match_and_download():
    if 'reference_image' not in request.files:
        return jsonify({'error': 'No reference image provided'}), 400

    reference_image = request.files['reference_image']
    temp_dir = 'temp'
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    reference_image_path = os.path.join(temp_dir, reference_image.filename)
    reference_image.save(reference_image_path)

    message, success = find_and_download_cluster(reference_image_path)

    if success:
        return jsonify({'message': message}), 200
    else:
        return jsonify({'error': message}), 500

if __name__ == '__main__':
    app.run(debug=True)
