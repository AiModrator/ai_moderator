import axios from "axios";
import { get } from "node:http";



export default class AxiosFactory {
    
    public constructor() {



        

    }

    public   getAxiosClient(url: string, headers?: any, timeout: number = 1000) {
        
        const instance = axios.create({
            baseURL: url ,
            timeout: timeout,
            headers: headers
        });

        const axiosClient: any = {}  ; 
        axiosClient.getNewContent = async (url: string, lastPolledAt: Date) => {
            instance.get(url, {
                params: {
                    since: lastPolledAt
                }
            })
        }


        return axiosClient ;
    } 
}

