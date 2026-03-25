import { prisma } from './prismaClient.js';
import {ApiKey as ApiKeyModel  , User as UserModel  ,
         ContentSource as ContentSourceModel , 
         Content as ContentModel ,
          Logs as LogsModel
        } from './generated/client.js'


export default prisma;


export type ApiKey =  ApiKeyModel
export type User =  UserModel
export type ContentSource =  ContentSourceModel
export type Content =  ContentModel
export type Logs =  LogsModel  
