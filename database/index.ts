import { prisma } from './prismaClient.js';
import {ApiKey as ApiKeyModel  , User as UserModel  ,
         ContentSource as ContentSourceModel , 
         Content as ContentModel ,
          ContentLogs as ContentLogsModel
        } from './generated/client.js'
import { appendFile } from 'node:fs';

export default prisma;


export type ApiKey =  ApiKeyModel
export type User =  UserModel
export type ContentSource =  ContentSourceModel
export type Content =  ContentModel
export type ContentLogs =  ContentLogsModel  
