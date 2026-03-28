



export const successResponse = (res:any, data:any, message = "success" , statusCode:number = 200) => {
  return res.status(statusCode).json({
    success: true,
    message,
    data,
  });
};



export const errorResponse = (res:any, message = "error", status = 500) => {
  return res.status(status).json({
    success: false,
    message,
  });
};