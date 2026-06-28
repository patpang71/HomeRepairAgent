import { readFileSync } from 'fs';
import { join } from 'path';
import { SecretsManagerClient, GetSecretValueCommand } from '@aws-sdk/client-secrets-manager';
import { Client } from 'pg';

const secretsManager = new SecretsManagerClient({});

interface DbSecret {
  host: string;
  port: number;
  dbname: string;
  username: string;
  password: string;
}

export const handler = async (event: { RequestType: string }): Promise<void> => {
  if (event.RequestType === 'Delete') return;

  const secretResponse = await secretsManager.send(
    new GetSecretValueCommand({ SecretId: process.env.DB_SECRET_ARN! }),
  );
  const secret: DbSecret = JSON.parse(secretResponse.SecretString!);

  const client = new Client({
    host: secret.host,
    port: secret.port,
    database: secret.dbname,
    user: secret.username,
    password: secret.password,
    ssl: { rejectUnauthorized: false },
  });

  await client.connect();

  try {
    const sql = readFileSync(join(__dirname, 'user_info_postgres.sql'), 'utf8');
    await client.query(sql);
    console.log('UserInfo schema initialized successfully');
  } finally {
    await client.end();
  }
};
